"""IT-46R1S2: actionable failure, honest partial results, and recovery.

Exercises the real app via its existing customer JSON upload API. Authentication
and the historical fixture clock are setup controls, not sign-in evidence. Only
the named unavailable dependency is fault-injected; no passing validation result
is fabricated. Browser rendering remains a separate integration boundary.
"""
from datetime import date
from hashlib import sha256
import importlib
import json
from pathlib import Path
import re

from fastapi.testclient import TestClient
import pytest

from app.services import required_data


ROOT = Path(required_data.__file__).resolve().parents[2]
FIXTURES = ROOT / "tests/fixtures/it_46/r1/s1"
OUTAGE = "IT-46R1S2 controlled dependency unavailable"


@pytest.fixture
def customer_validation_client(monkeypatch):
    main = importlib.import_module("app.main")
    routes = importlib.import_module("app.api.routes")
    validation = importlib.import_module("app.services.validation")
    chronology = importlib.import_module("app.services.date_chronology_required_data")
    manifest = json.loads((FIXTURES / "manifest.json").read_text(encoding="utf-8"))

    class HistoricalDate(date):
        @classmethod
        def today(cls):
            return cls.fromisoformat(manifest["evaluation_date"])

    monkeypatch.setattr(chronology, "date", HistoricalDate)
    monkeypatch.setenv("WORKOS_CLIENT_ID", "client_it46_failure_setup")
    monkeypatch.setenv("WORKOS_REDIRECT_URI", "http://testserver/auth/callback")
    monkeypatch.setattr(main, "WorkOSClient", lambda **kwargs: object())

    def identity(request, _workos):
        assert request.cookies.get("wos_session") == "it46-failure-session"
        return {"id": "user_it46_failure_setup"}

    monkeypatch.setattr(main, "_authenticated_workos_user", identity)
    monkeypatch.setattr(main.app.state, "workos_identity_account_links", {
        "user_it46_failure_setup": "account_it46_failure_setup",
    })
    monkeypatch.setattr(routes, "validation_service", validation.ValidationService())
    with TestClient(main.app, raise_server_exceptions=False) as client:
        client.cookies.set("wos_session", "it46-failure-session")
        yield client, validation, manifest


def submit(client, name, payload):
    response = client.post("/validate/uad36", json={
        "package_name": name,
        "xml_text": payload.decode("utf-8"),
        "investor_scope": "both",
    })
    assert "application/json" in response.headers.get("content-type", ""), (
        "IT-46R1S2 requires a structured customer failure result, not a bare "
        f"server error. Received HTTP {response.status_code}: {response.text[:200]}"
    )
    report = response.json()
    assert isinstance(report, dict) and report.get("run_id"), (
        "IT-46R1S2 requires a retrievable validation run identifying the failed "
        "request, including any incomplete results."
    )
    assert response.status_code in {200, 400, 422, 503}
    return report


@pytest.mark.parametrize("case", [
    "unclosed-xml", "mismatched-xml", "schema-execution-failure",
    "business-execution-failure", "partial-rule-execution-failure",
])
def test_it_46_r1_s2_returns_actionable_failure_and_allows_corrected_upload_or_retry(
    case, customer_validation_client, monkeypatch, record_property,
):
    record_property("scenario_id", "IT-46R1S2")
    client, validation, manifest = customer_validation_client
    selected = {row["Message ID"] for row in required_data.load_required_rules()}
    baseline_case = next(c for c in manifest["cases"] if c["id"] == "schema-valid-baseline")
    missing_case = next(c for c in manifest["cases"] if c["id"] == "missing-address")
    baseline_path = FIXTURES / baseline_case["file"]
    missing_path = FIXTURES / missing_case["file"]
    baseline, missing = baseline_path.read_bytes(), missing_path.read_bytes()
    assert sha256(baseline).hexdigest() == baseline_case["sha256"]
    assert sha256(missing).hexdigest() == missing_case["sha256"]
    malformed = case in {"unclosed-xml", "mismatched-xml"}
    payload = {
        "unclosed-xml": b'<MESSAGE xmlns="http://www.mismo.org/residential/2009/schemas">',
        "mismatched-xml": b'<MESSAGE><ADDRESS></MESSAGE>',
    }.get(case, missing if case == "partial-rule-execution-failure" else baseline)
    unavailable_rule = None

    def unavailable(*args, **kwargs):
        raise RuntimeError(OUTAGE)

    # Restore the failed dependency before retrying the same customer endpoint.
    with monkeypatch.context() as fault:
        if case == "schema-execution-failure":
            fault.setattr(validation, "validate_uad36_xml_bytes", unavailable)
        elif case == "business-execution-failure":
            fault.setattr(validation, "evaluate_required_data", unavailable)
        elif case == "partial-rule-execution-failure":
            row = next(row for row in required_data.load_required_rules()
                       if required_data.numeric_bound_binding_for(row) is not None)
            unavailable_rule = row["Message ID"]
            real_numeric = required_data.evaluate_numeric_bound

            def fail_one_rule(root, investor, rule):
                if rule["Message ID"] == unavailable_rule:
                    raise RuntimeError(OUTAGE)
                return real_numeric(root, investor, rule)

            fault.setattr(required_data, "evaluate_numeric_bound", fail_one_rule)
        report = submit(client, f"{case}.xml", payload)

    assert report.get("passed") is False, "An execution failure must never be reported as passing."
    assert report.get("processing_status") in {"failed", "incomplete"}
    failure = report.get("failure")
    assert isinstance(failure, dict), (
        "IT-46R1S2 requires a customer-facing failure explanation and suggested "
        "action in the validation result. A finding count or technical exception "
        "alone does not explain whether to correct the XML or retry the service."
    )
    message, action = failure.get("message"), failure.get("suggested_action")
    assert isinstance(message, str) and message.strip()
    assert isinstance(action, str) and action.strip()
    if malformed:
        assert re.search(r"xml|pars|well.formed", message, re.I)
        assert re.search(r"correct|repair|fix|export", action, re.I)
        assert re.search(r"submit|upload|try", action, re.I)
    else:
        assert re.search(r"unavailable|unable|could not|cannot|fail|incomplete", message, re.I)
        assert re.search(r"retry|try again", action, re.I)

    coverage = report.get("coverage")
    assert isinstance(coverage, dict), "Failure must explicitly identify unevaluated checks."
    assert coverage["complete"] is False
    evaluated = set(coverage["evaluated_rule_ids"])
    skipped = coverage["not_evaluated"]
    skipped_ids = [item["rule_id"] for item in skipped]
    assert set(coverage["selected_rule_ids"]) == selected
    assert skipped and len(skipped_ids) == len(set(skipped_ids))
    assert evaluated.isdisjoint(skipped_ids)
    assert evaluated | set(skipped_ids) == selected
    assert all(isinstance(item.get("reason"), str) and item["reason"].strip() for item in skipped)
    if malformed or case == "business-execution-failure":
        assert not evaluated, "Checks that did not run cannot be counted as completed."
    if case == "business-execution-failure":
        assert report["schema"]["schema_valid"] is True
        assert report["processing_status"] == "incomplete", "Available schema results are partial."
    if unavailable_rule:
        assert report["processing_status"] == "incomplete"
        assert unavailable_rule in skipped_ids and unavailable_rule not in evaluated
        assert "UAD1001" in evaluated
        assert any(f.get("rule_id") == "UAD1001" for f in report["findings"]), (
            "The independent missing-address finding must remain available as a partial result."
        )

    saved = client.get(f"/validation-runs/{report['run_id']}")
    assert saved.status_code == 200 and saved.json() == report
    retry = submit(client, "corrected-or-retried-SF1.xml", baseline)
    assert retry["run_id"] != report["run_id"]
    assert retry["processing_status"] == "completed" and retry["passed"] is True
    assert retry["coverage"]["complete"] is True
    assert retry["coverage"]["not_evaluated"] == []
    assert retry.get("failure") is None
    assert retry["source_sha256"] == sha256(baseline).hexdigest()
    assert client.get(f"/validation-runs/{report['run_id']}").json() == report
    assert baseline_path.read_bytes() == baseline and missing_path.read_bytes() == missing
