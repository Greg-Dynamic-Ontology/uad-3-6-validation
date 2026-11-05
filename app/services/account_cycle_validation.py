"""IT-64: durable account cycles around the existing IT-25 lifecycle workers."""
from dataclasses import asdict, replace
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from threading import RLock
from types import SimpleNamespace
from uuid import uuid4

from rdflib import Graph, RDF, RDFS

from app.adapters.customer_validation_store import CustomerValidationStore
from app.models.validation import ValidationRequest, ValidationRun
from app.services import validation_cycles as lifecycle
from app.services.gse_constraint_sources import CFG, APP_CONFIGURATION_TYPE, read_active_compliance_workbook_rows
from app.services.required_data import ROOT, load_required_rules
from app.services.validation import validation_service
from app.services.validation_credits import ValidationCreditLot, consume_validation_credit
from app.services.xml_schema_validator import UAD36_SCHEMA_PATH, UAD36_SCHEMA_VERSION


_ENGINE_LOCK = RLock()


def now():
    return datetime.now(timezone.utc)


def encoded(value):
    return json.dumps(value, default=lambda item: item.isoformat() if isinstance(item, datetime) else asdict(item))


def current_coverage():
    """Identify the governed schema and the explicitly selected workbook coverage."""
    configuration = ROOT / "config/configuration.ttl"
    graph = Graph().parse(configuration, format="turtle")
    application = tuple(graph.subjects(RDF.type, APP_CONFIGURATION_TYPE))
    if len(application) != 1:
        raise ValueError("One governed application configuration is required.")
    sources = tuple(graph.objects(application[0], CFG.activeComplianceSource))
    if len(sources) != 1:
        raise ValueError("One active constraint source is required.")
    source = read_active_compliance_workbook_rows(configuration_path=configuration)
    digest = sha256(source.workbook_path.read_bytes()).hexdigest()
    supported = load_required_rules()
    rule_ids = sorted({r["Message ID"] for r in supported})
    if not rule_ids or any(Path(r["_source_document"]).resolve() != source.workbook_path.resolve() for r in supported):
        raise ValueError("The engine's loaded rules do not match the selected governed source.")
    return {
        "schema": {"version": UAD36_SCHEMA_VERSION,
                   "sha256": sha256(UAD36_SCHEMA_PATH.read_bytes()).hexdigest(),
                   "source_document": str(UAD36_SCHEMA_PATH)},
        "constraint_sets": [{"constraint_set_id": str(sources[0]),
                             "version": "sha256:" + digest,
                             "source_document": str(source.workbook_path),
                             "source_sha256": digest, "worksheet": source.worksheet_name,
                             "label": str(graph.value(sources[0], RDFS.label) or sources[0]),
                             "evaluated_rule_ids": rule_ids,
                             "supported_rule_count": len(rule_ids),
                             "published_row_count": len(source.rows)}],
        "evaluation_scope": {
            "engine": "app.services.validation.ValidationService.validate",
            "xml_check": "Governed XSD assessment and selected workbook rules",
            "full_xsd_validation_performed": True,
            "shacl_validation_performed": False,
            "business_rules": "Only the explicitly listed supported workbook rules",
        },
    }


class CycleStore:
    def __init__(self, store=None):
        self.store = store or CustomerValidationStore()

    def initialize(self):
        with self.store.connection() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS cv_cycles (
                    cycle_id TEXT PRIMARY KEY REFERENCES account_validation_cycles(validation_cycle_id),
                    document TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS cv_requests (
                    account_id TEXT NOT NULL, request_key TEXT NOT NULL, request_digest TEXT NOT NULL,
                    cycle_id TEXT NOT NULL REFERENCES cv_cycles(cycle_id), PRIMARY KEY(account_id,request_key));
                CREATE TABLE IF NOT EXISTS cv_submissions (
                    submission_id TEXT PRIMARY KEY, cycle_id TEXT NOT NULL REFERENCES cv_cycles(cycle_id),
                    document TEXT NOT NULL, content BLOB NOT NULL);
                CREATE TABLE IF NOT EXISTS cv_attempts (
                    attempt_id TEXT PRIMARY KEY, cycle_id TEXT NOT NULL REFERENCES cv_cycles(cycle_id), document TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS cv_results (
                    result_id TEXT PRIMARY KEY, cycle_id TEXT NOT NULL REFERENCES cv_cycles(cycle_id),
                    run_id TEXT NOT NULL UNIQUE, document TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS cv_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT, cycle_id TEXT NOT NULL REFERENCES cv_cycles(cycle_id),
                    kind TEXT NOT NULL, document TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS cv_credit_lots (
                    lot_id TEXT PRIMARY KEY, account_id TEXT NOT NULL REFERENCES entry_accounts(customer_account_id),
                    payment_id TEXT NOT NULL, remaining INTEGER NOT NULL CHECK(remaining >= 0));
                CREATE TABLE IF NOT EXISTS cv_credit_history (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT, document TEXT NOT NULL);
            ''')

    def available_credits(self, account_id):
        with self.store.connection() as db:
            if not db.execute("SELECT 1 FROM sqlite_master WHERE name='cv_credit_lots'").fetchone():
                return 0
            return db.execute("SELECT COALESCE(SUM(remaining),0) FROM cv_credit_lots WHERE account_id=?", (account_id,)).fetchone()[0]

    def detail(self, cycle_id, account_id):
        with self.store.connection() as db:
            if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='cv_cycles'").fetchone():
                return None
            owned = db.execute("SELECT 1 FROM account_validation_cycles WHERE validation_cycle_id=? AND customer_account_id=?",
                               (cycle_id, account_id)).fetchone()
            if not owned:
                return None
            row = db.execute("SELECT document FROM cv_cycles WHERE cycle_id=?", (cycle_id,)).fetchone()
            if not row:
                return None
            cycle = json.loads(row[0])
            submissions = [json.loads(r[0]) for r in db.execute("SELECT document FROM cv_submissions WHERE cycle_id=? ORDER BY rowid", (cycle_id,))]
            attempts = [json.loads(r[0]) for r in db.execute("SELECT document FROM cv_attempts WHERE cycle_id=? ORDER BY rowid", (cycle_id,))]
            result = db.execute("SELECT document FROM cv_results WHERE result_id=?", (cycle.get("current_validation_result_id"),)).fetchone()
            events = [(r[0], json.loads(r[1])) for r in db.execute("SELECT kind,document FROM cv_events WHERE cycle_id=? ORDER BY event_id", (cycle_id,))]
            return {"cycle": cycle, "submissions": submissions, "attempts": attempts,
                    "current_result": json.loads(result[0]) if result else None,
                    "history": [e for kind, e in events if kind == "history"],
                    "credit_lifecycle_events": [e for kind, e in events if kind == "credit"]}

    def run(self, run_id):
        with self.store.connection() as db:
            if not db.execute("SELECT 1 FROM sqlite_master WHERE name='cv_results'").fetchone():
                return None
            row = db.execute("SELECT r.document,c.customer_account_id FROM cv_results r JOIN account_validation_cycles c ON c.validation_cycle_id=r.cycle_id WHERE r.run_id=?", (run_id,)).fetchone()
            return (json.loads(row[0])["validation_run"], row[1]) if row else None


class Repository:
    """Transaction-bound adapters for the existing lifecycle and credit services."""
    def __init__(self, db, cycle_id):
        self.db, self.cycle_id = db, cycle_id

    def get_by_id(self, cycle_id):
        row = self.db.execute("SELECT document FROM cv_cycles WHERE cycle_id=?", (cycle_id,)).fetchone()
        if not row:
            return None
        value = json.loads(row[0])
        value["created_at"] = datetime.fromisoformat(value["created_at"])
        return lifecycle.PendingValidationCycle(**value)

    def save(self, cycle):
        previous = self.get_by_id(cycle.validation_cycle_id)
        self.db.execute("INSERT INTO account_validation_cycles VALUES(?,?,?) ON CONFLICT(validation_cycle_id) DO UPDATE SET state=excluded.state",
                        (cycle.validation_cycle_id, cycle.customer_account_id, cycle.state))
        self.db.execute("INSERT INTO cv_cycles VALUES(?,?) ON CONFLICT(cycle_id) DO UPDATE SET document=excluded.document",
                        (cycle.validation_cycle_id, encoded(cycle)))
        if previous is None or previous.state != cycle.state:
            self.event("history", {"previous_state": previous.state if previous else None,
                                   "current_state": cycle.state, "effective_at": now().isoformat()})

    def event(self, kind, value):
        self.db.execute("INSERT INTO cv_events(cycle_id,kind,document) VALUES(?,?,?)", (self.cycle_id, kind, encoded(value)))

    def retain(self, artifact, integrity_digest):
        self.artifact = artifact
        return "sqlite:cv_submissions/" + self.submission_id

    def save_submission(self, submission):
        self.db.execute("INSERT INTO cv_submissions VALUES(?,?,?,?)", (submission.validation_submission_id,
                        self.cycle_id, encoded({**asdict(submission), "package_name": self.artifact.report_id}), self.artifact.content))

    def submission_belongs_to_cycle(self, cycle_id, submission_id):
        return self.db.execute("SELECT 1 FROM cv_submissions WHERE submission_id=? AND cycle_id=?", (submission_id, cycle_id)).fetchone() is not None

    def get_active_for_cycle(self, cycle_id):
        for row in self.db.execute("SELECT document FROM cv_attempts WHERE cycle_id=?", (cycle_id,)):
            if json.loads(row[0])["state"] == "running":
                return json.loads(row[0])
        return None

    def save_attempt(self, attempt):
        self.db.execute("INSERT INTO cv_attempts VALUES(?,?,?)", (attempt.validation_attempt_id, self.cycle_id, encoded(attempt)))

    def save_result(self, result):
        self.result = result

    def publish(self, event):
        self.event("credit", asdict(event))

    def append_history_event(self, cycle_id, event):
        self.event("history", asdict(event))


class CreditRepository:
    def __init__(self, db):
        self.db = db

    def save(self, lot):
        self.db.execute("UPDATE cv_credit_lots SET remaining=? WHERE lot_id=?", (lot.remaining_quantity, lot.validation_credit_lot_id))

    def record(self, **event):
        self.db.execute("INSERT INTO cv_credit_history(document) VALUES(?)", (encoded({**event, "effective_at": now().isoformat()}),))


def submit_new_cycle(*, account_id, actor_id, package_name, content, request_key):
    """Commit acceptance/debit, execute real validation, then commit its outcome."""
    store = CycleStore()
    store.initialize()
    request_digest = sha256(package_name.encode() + b"\0" + content).hexdigest()
    cycle_id = str(uuid4())
    with store.store.connection() as db:
        db.execute("BEGIN IMMEDIATE")
        existing = db.execute("SELECT request_digest,cycle_id FROM cv_requests WHERE account_id=? AND request_key=?", (account_id, request_key)).fetchone()
        if existing:
            if existing[0] != request_digest:
                raise ValueError("Idempotency key already identifies different report content.")
            return existing[1]
        lot_row = db.execute("SELECT lot_id,account_id,payment_id,remaining FROM cv_credit_lots WHERE account_id=? AND remaining>0 ORDER BY rowid LIMIT 1", (account_id,)).fetchone()
        if not lot_row:
            raise PermissionError("An available account validation credit is required to start a new cycle.")
        repo = Repository(db, cycle_id)
        artifact = SimpleNamespace(report_id=package_name, content=content)
        cycle = lifecycle.create_pending_validation_cycle(account_id, actor_id, artifact, lambda: cycle_id, now, repo)
        repo.submission_id = str(uuid4())
        submission = lifecycle.accept_report_submission(cycle_id, artifact, lambda: repo.submission_id, now, repo, repo)
        attempt = lifecycle.start_validation_attempt(cycle_id, submission.validation_submission_id, lambda: str(uuid4()), now, lambda attempt: None, repo)
        credit_lot = ValidationCreditLot(*lot_row)
        credits = CreditRepository(db)
        consume_validation_credit(credit_lot, actor_id, credits, credits)
        db.execute("INSERT INTO cv_requests VALUES(?,?,?,?)", (account_id, request_key, request_digest, cycle_id))
    # The pending cycle/submission/attempt are committed before execution starts.
    try:
        with _ENGINE_LOCK:
            load_required_rules.cache_clear()
            coverage = current_coverage()
            run = validation_service.validate(ValidationRequest(package_name=package_name, xml_text=content.decode("utf-8-sig")))
            if current_coverage() != coverage:
                raise RuntimeError("Governed coverage changed during validation; no passing result may be certified.")
        # Non-readable input cannot become an actionable appraisal result.
        if run.processing_status != "completed" or not run.schema_assessment or not run.schema_assessment.well_formed:
            raise ValueError("The report could not produce a complete actionable result. Execution credit was restored.")
        if (not run.coverage or not run.coverage.complete
                or sorted(run.coverage.evaluated_rule_ids) != coverage["constraint_sets"][0]["evaluated_rule_ids"]
                or run.coverage.constraint_set.sha256 != coverage["constraint_sets"][0]["source_sha256"]
                or run.schema_assessment.sha256 != coverage["schema"]["sha256"]):
            raise RuntimeError("Recorded coverage does not match actual completed validation.")
        with store.store.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            repo = Repository(db, cycle_id)
            result = lifecycle.produce_actionable_validation_result(
                submission.validation_submission_id,
                SimpleNamespace(ingestible=True, findings=tuple(run.findings) + tuple(run.schema_assessment.findings)),
                lambda: str(uuid4()), now, repo)
            document = {**asdict(result), "validation_cycle_id": cycle_id,
                        "validation_attempt_id": attempt.validation_attempt_id,
                        "validation_run_id": run.run_id, "validation_run": run.model_dump(mode="json", by_alias=True),
                        "findings": [f.model_dump(mode="json") for f in result.findings], **coverage}
            db.execute("INSERT INTO cv_results VALUES(?,?,?,?)", (result.validation_result_id, cycle_id, run.run_id, encoded(document)))
            lifecycle.apply_first_actionable_validation_result(cycle_id, result, now, repo, repo)
            db.execute("UPDATE cv_attempts SET document=? WHERE attempt_id=?", (encoded({**asdict(attempt), "state": "completed"}), attempt.validation_attempt_id))
    except Exception:
        with store.store.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            repo = Repository(db, cycle_id)
            lifecycle.cancel_pending_cycle_for_validation_service_failure(cycle_id, submission.validation_submission_id,
                                                                         "Production validation could not complete; no actionable result was issued.", now, repo, repo)
            db.execute("UPDATE cv_credit_lots SET remaining=remaining+1 WHERE lot_id=?", (credit_lot.validation_credit_lot_id,))
            CreditRepository(db).record(event_type="validation_credit_restored", validation_cycle_id=cycle_id,
                                        customer_account_id=account_id, actor_id=actor_id, quantity=1)
            db.execute("UPDATE cv_attempts SET document=? WHERE attempt_id=?", (encoded({**asdict(attempt), "state": "failed"}), attempt.validation_attempt_id))
        raise
    return cycle_id
