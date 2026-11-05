"""IT-46R2S1: real browser review and download of a real validation run.

Starts its own local Uvicorn server. Real XSD/business evaluators create the
results; authentication is isolated setup, not a claim of hosted sign-in QA.
Only one deliberate evaluator outage and the historical sample clock are
controlled. No route responses, result rendering, or downloads are mocked.

UI contract: a visible run container carries data-validation-run-id; finding
entries carry data-finding-id. The Download report action exports JSON with
the original run identity, findings, and coverage. These hooks identify actual
displayed results rather than hidden JavaScript state.
"""
from datetime import date
from hashlib import sha256
import importlib
import json
from pathlib import Path
import re
import socket
from threading import Thread
from time import monotonic, sleep
from xml.etree import ElementTree as ET

import pytest
from playwright.sync_api import expect
import uvicorn

from app.services import required_data


ROOT = Path(required_data.__file__).resolve().parents[2]
FIXTURES = ROOT / "tests/fixtures/it_46/r1/s1"
NAMESPACES = {"m": required_data.NAMESPACE}
OUTAGE = "IT-46R2S1 controlled numeric evaluator unavailable"


@pytest.fixture
def result_review_server(monkeypatch, page):
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
    monkeypatch.setenv("WORKOS_CLIENT_ID", "client_it46_result_review_setup")
    monkeypatch.setenv("WORKOS_REDIRECT_URI", "http://testserver/auth/callback")
    monkeypatch.setattr(main, "WorkOSClient", lambda **kwargs: object())

    def identity(request, _workos):
        if request.cookies.get("wos_session") == "it46-review-session":
            return {"id": "user_it46_result_review_setup"}
        return None

    monkeypatch.setattr(main, "_authenticated_workos_user", identity)
    monkeypatch.setattr(main.app.state, "workos_identity_account_links", {
        "user_it46_result_review_setup": "account_it46_result_review_setup",
    })
    service = validation.ValidationService()
    calls = []
    real_validate = service.validate

    def observe_validation(request):
        calls.append(request.package_name)
        return real_validate(request)

    monkeypatch.setattr(service, "validate", observe_validation)
    monkeypatch.setattr(routes, "validation_service", service)
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(("127.0.0.1", 0))
    host, port = server_socket.getsockname()
    url = f"http://{host}:{port}"
    server = uvicorn.Server(uvicorn.Config(
        main.app, host=host, port=port, log_level="error", ws="none",
    ))
    thread = Thread(target=server.run, kwargs={"sockets": [server_socket]}, daemon=True)
    try:
        thread.start()
        deadline = monotonic() + 10
        while not server.started and monotonic() < deadline:
            sleep(0.01)
        assert server.started, "IT-46R2S1 setup: local test server did not start."
        page.context.add_cookies([{
            "name": "wos_session", "value": "it46-review-session",
            "url": url, "httpOnly": True, "sameSite": "Lax",
        }])
        yield url, manifest, calls
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        server_socket.close()


def occurrence_key(finding):
    return (
        finding.get("rule_id"), finding.get("row_id"),
        finding.get("graph_resource_iri") or finding.get("data_location"),
        finding.get("observed_value"),
    )


@pytest.mark.parametrize("case", ["no-findings", "actionable-findings", "incomplete-findings"])
def test_it_46_r2_s1_reviews_honest_coverage_and_downloads_the_same_run(
    case, result_review_server, page, monkeypatch, tmp_path, record_property,
):
    record_property("scenario_id", "IT-46R2S1")
    url, manifest, calls = result_review_server
    source_case = next(c for c in manifest["cases"] if c["id"] == (
        "schema-valid-baseline" if case == "no-findings" else "missing-address"
    ))
    source_path = FIXTURES / source_case["file"]
    original = source_path.read_bytes()
    assert sha256(original).hexdigest() == source_case["sha256"]
    payload = original
    if case != "no-findings":
        # A second governed defect makes ordering/deduplication nontrivial.
        # UAD1002 / row 0100.0009 is recorded in the existing source manifest.
        tree = ET.fromstring(original)
        address = tree.find(".//m:VALUATION_ANALYSIS/m:PROPERTIES/"
                            "m:PROPERTY[@ValuationUseType='SubjectProperty']/m:ADDRESS", NAMESPACES)
        assert address is not None
        city = address.find("m:CityName", NAMESPACES)
        assert city is not None
        address.remove(city)
        payload = ET.tostring(tree, encoding="utf-8", xml_declaration=True)

    with monkeypatch.context() as fault:
        unavailable_id = None
        if case == "incomplete-findings":
            rule = next(r for r in required_data.load_required_rules()
                        if required_data.numeric_bound_binding_for(r) is not None)
            unavailable_id = rule["Message ID"]
            real_numeric = required_data.evaluate_numeric_bound

            def controlled_outage(root, investor, rule):
                if rule["Message ID"] == unavailable_id:
                    raise RuntimeError(OUTAGE)
                return real_numeric(root, investor, rule)

            fault.setattr(required_data, "evaluate_numeric_bound", controlled_outage)
        response = page.request.post(f"{url}/validate/uad36", data={
            "package_name": f"IT46R2S1-{case}.xml",
            "xml_text": payload.decode("utf-8"), "investor_scope": "both",
        })
        assert response.status == 200, response.text()
        report = response.json()

    # Preconditions verify real results before testing their presentation.
    assert len(calls) == 1
    findings = report["findings"]
    coverage = report["coverage"]
    assert report["source_sha256"] == sha256(payload).hexdigest()
    if case == "no-findings":
        assert findings == [] and report["passed"] is True
    else:
        assert {"UAD1001", "UAD1002"} <= {f["rule_id"] for f in findings}
        assert report["passed"] is False
    assert coverage["complete"] is (case != "incomplete-findings")
    keys = [occurrence_key(f) for f in findings]
    assert len(keys) == len(set(keys)), "Duplicate findings for the same constraint and occurrence."

    # Given the run already exists, open that specific result for review.
    page.goto(f"{url}/validation/?run_id={report['run_id']}")
    result = page.locator(f'[data-validation-run-id="{report["run_id"]}"]')
    expect(result, message=(
        "IT-46R2S1 requires opening the saved run in the customer browser, "
        "with its run identity, actual findings, and honest coverage summary."
    )).to_be_visible()
    expect(result).to_contain_text(report["run_id"])
    expect(result).to_contain_text(re.compile(
        r"incomplete" if case == "incomplete-findings" else r"completed", re.I,
    ))
    expect(result).to_contain_text(re.compile(
        r"no (?:issues|findings).*evaluated|no (?:issues|findings).*selected"
        if case == "no-findings" else r"findings (?:detected|found)|issues (?:detected|found)", re.I,
    ))
    expect(result).to_contain_text(re.compile(r"selected.*coverage|evaluated.*coverage", re.I))
    expect(result).to_contain_text(re.compile(
        r"(?:outside|unselected|not selected|not evaluated).*" 
        r"(?:coverage|constraints|rules)|does not establish complete.*compliance", re.I,
    ))
    coverage_panel = result.locator('[data-validation-coverage]')
    expect(coverage_panel).to_be_visible()
    # Named counts prevent accidental matches against unrelated numbers/IDs.
    for name, count in {
        "selected": len(coverage["selected_rule_ids"]),
        "evaluated": len(coverage["evaluated_rule_ids"]),
        "not-evaluated": len(coverage["not_evaluated"]),
    }.items():
        expect(coverage_panel.locator(f'[data-coverage-count="{name}"]')).to_have_text(str(count))

    for finding in findings:
        entry = result.locator(f'[data-finding-id="{finding["finding_id"]}"]')
        expect(entry).to_be_visible()
        for details in entry.locator("details").all():
            if details.get_attribute("open") is None:
                details.locator("summary").click()
        for field in ("rule_id", "row_id", "severity", "finding", "expected_condition", "data_location"):
            assert finding.get(field), f"Missing governed finding field: {field}"
            expect(entry).to_contain_text(re.compile(re.escape(finding[field]), re.I))
    displayed_ids = result.locator("[data-finding-id]").evaluate_all(
        "entries => entries.map(entry => entry.dataset.findingId)"
    )
    assert displayed_ids == [f["finding_id"] for f in findings], "Displayed findings must match the saved ordered list."
    if unavailable_id:
        expect(coverage_panel).to_contain_text(unavailable_id)
        reason = next(item["reason"] for item in coverage["not_evaluated"] if item["rule_id"] == unavailable_id)
        expect(coverage_panel).to_contain_text(reason)
        assert unavailable_id not in coverage["evaluated_rule_ids"]
        assert not re.search(r"\bPASSED\b|validation (?:passed|successful)", result.inner_text(), re.I)

    # Inspect a real browser download, not a mocked URL or hidden JS object.
    with page.expect_download() as pending:
        result.get_by_role("link", name=re.compile(r"download.*report", re.I)).click()
    download = pending.value
    assert download.failure() is None
    path = tmp_path / "downloaded-validation-report.json"
    download.save_as(str(path))
    exported = json.loads(path.read_text(encoding="utf-8-sig"))
    for field in ("run_id", "package_name", "source_sha256", "processing_status", "passed",
                  "schema", "coverage", "findings", "failure"):
        assert exported[field] == report[field], f"Downloaded {field} differs from the reviewed run."
    page.reload()
    expect(result).to_be_visible()
    assert result.locator("[data-finding-id]").evaluate_all(
        "entries => entries.map(entry => entry.dataset.findingId)"
    ) == displayed_ids, "Reopening the result changed finding order or duplicated entries."
    saved = page.request.get(f"{url}/validation-runs/{report['run_id']}")
    assert saved.status == 200 and saved.json() == report
    assert len(calls) == 1, "Reviewing or downloading must not rerun validation."
    assert source_path.read_bytes() == original, "Review changed the source fixture."
