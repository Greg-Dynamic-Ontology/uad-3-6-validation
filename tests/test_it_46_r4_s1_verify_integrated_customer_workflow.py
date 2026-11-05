"""IT-46R4S1: actual customer upload-to-report integration acceptance.

Reuses all 53 existing required-data negative fixtures plus an established
conditional case. Real application, network requests, XSD/business validation,
browser controls, and downloads run without response substitution. Only auth
setup, historical sample clock, and one intentional evaluator outage are
controlled. Full repository regression is a separate release gate, not a
recursive pytest invocation or a claim inferred from this scenario test.
"""
from datetime import date
from hashlib import sha256
import csv
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


@pytest.fixture
def workflow_server(monkeypatch, page):
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
        calls.append((request.package_name, sha256(request.xml_text.encode("utf-8")).hexdigest()))
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
        assert server.started, "IT-46R4S1 setup: local test server did not start."
        page.context.add_cookies([{
            "name": "wos_session", "value": "it46-review-session",
            "url": url, "httpOnly": True, "sameSite": "Lax",
        }])
        yield url, manifest, calls
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        server_socket.close()




CORPUS = ROOT / "data/uad36-test-suite/tests/fixtures/required_data"
with (CORPUS / "manifest.csv").open(newline="", encoding="utf-8-sig") as handle:
    NEGATIVES = list(csv.DictReader(handle))
assert len(NEGATIVES) == 53, "Review corpus changes explicitly rather than silently reducing integration coverage."


def baseline_bytes(manifest):
    case = next(c for c in manifest["cases"] if c["id"] == "schema-valid-baseline")
    path = FIXTURES / case["file"]
    payload = path.read_bytes()
    assert sha256(payload).hexdigest() == case["sha256"]
    return path, payload


def assert_recorded_coverage(report, payload):
    from app.services.xml_schema_validator import UAD36_SCHEMA_PATH, UAD36_SCHEMA_VERSION
    assert report["source_sha256"] == sha256(payload).hexdigest()
    assert report["schema"]["schema_version"] == UAD36_SCHEMA_VERSION
    assert report["schema"]["sha256"] == sha256(UAD36_SCHEMA_PATH.read_bytes()).hexdigest()
    coverage = report["coverage"]
    selected = set(coverage["selected_rule_ids"])
    assert selected == {r["Message ID"] for r in required_data.load_required_rules()}
    evaluated = set(coverage["evaluated_rule_ids"])
    skipped = {item["rule_id"] for item in coverage["not_evaluated"]}
    assert evaluated.isdisjoint(skipped) and evaluated | skipped == selected
    assert coverage["complete"] is (not skipped)
    assert all(item["reason"].strip() for item in coverage["not_evaluated"])
    assert coverage["constraint_set"]["version"] and coverage["constraint_set"]["sha256"]


def download_same_report(page, report, tmp_path):
    result = page.locator(f'[data-validation-run-id="{report["run_id"]}"]')
    expect(result).to_be_visible()
    expect(result).to_contain_text(report["run_id"])
    with page.expect_download() as pending:
        result.get_by_role("link", name=re.compile(r"download.*report", re.I)).click()
    download = pending.value
    assert download.failure() is None
    destination = tmp_path / f'{report["run_id"]}.json'
    download.save_as(str(destination))
    exported = json.loads(destination.read_text(encoding="utf-8-sig"))
    assert exported == report, "The download must be the same actual validation run."
    return result


def browser_submit(page, url, name, payload):
    page.locator("#appraisal-file").set_input_files({
        "name": name, "mimeType": "application/xml", "buffer": payload,
    })
    with page.expect_response(lambda reply:
        reply.request.method == "POST" and "/validate/uad36" in reply.url
    ) as pending:
        page.locator("#validate-button").click()
    response = pending.value
    assert response.url == f"{url}/validate/uad36", (
        "IT-46R4S1 requires the fresh customer upload path to execute governed "
        "schema and business validation and produce a reportable run. "
        f"The browser instead submitted to {response.url}."
    )
    assert response.status == 200, response.text()
    return response.json()


def test_it_46_r4_s1_browser_upload_result_download_and_corrected_resubmission(
    workflow_server, page, tmp_path, record_property,
):
    record_property("scenario_id", "IT-46R4S1")
    url, manifest, calls = workflow_server
    source, baseline = baseline_bytes(manifest)
    negative_case = next(row for row in NEGATIVES if row["rule_id"] == "UAD1001")
    negative_path = CORPUS / "tests" / negative_case["filename"]
    negative = negative_path.read_bytes()
    # Fresh customer entry, not a saved-run/developer shortcut.
    page.goto(f"{url}/validation/")
    positive = browser_submit(page, url, "positive-SF1.xml", baseline)
    assert positive["processing_status"] == "completed" and positive["passed"] is True
    assert positive["schema"]["schema_valid"] is True and positive["findings"] == []
    assert_recorded_coverage(positive, baseline)
    download_same_report(page, positive, tmp_path)

    defective = browser_submit(page, url, negative_path.name, negative)
    assert_recorded_coverage(defective, negative)
    assert defective["run_id"] != positive["run_id"] and defective["passed"] is False
    expected = [f for f in defective["findings"] if f["rule_id"] == "UAD1001"]
    assert len(expected) == 1
    assert expected[0]["row_id"] == negative_case["row_id"]
    assert expected[0]["data_location"] == negative_case["xml_path_context"]
    result = download_same_report(page, defective, tmp_path)
    expect(result.locator(f'[data-finding-id="{expected[0]["finding_id"]}"]')).to_contain_text("UAD1001")

    corrected = browser_submit(page, url, "corrected-SF1.xml", baseline)
    assert_recorded_coverage(corrected, baseline)
    assert len({positive["run_id"], defective["run_id"], corrected["run_id"]}) == 3
    assert corrected["passed"] is True and corrected["findings"] == []
    assert corrected["package_name"] == "corrected-SF1.xml"
    assert corrected["source_sha256"] != defective["source_sha256"]
    result = download_same_report(page, corrected, tmp_path)
    expect(result.locator("[data-finding-id]")).to_have_count(0)
    for report in (positive, defective, corrected):
        saved = page.request.get(f"{url}/validation-runs/{report['run_id']}")
        assert saved.status == 200 and saved.json() == report
    assert len(calls) == 3
    assert source.read_bytes() == baseline and negative_path.read_bytes() == negative


@pytest.mark.parametrize("row", NEGATIVES, ids=[row["rule_id"] for row in NEGATIVES])
def test_it_46_r4_s1_existing_negative_fixture_in_result_and_download(
    row, workflow_server, page, tmp_path, record_property,
):
    record_property("scenario_id", "IT-46R4S1")
    url, _manifest, calls = workflow_server
    path = CORPUS / "tests" / row["filename"]
    payload = path.read_bytes()
    response = page.request.post(f"{url}/validate/uad36", data={
        "package_name": path.name, "xml_text": payload.decode("utf-8"), "investor_scope": "both",
    })
    assert response.status == 200, response.text()
    report = response.json()
    assert_recorded_coverage(report, payload)
    assert row["rule_id"] in report["coverage"]["evaluated_rule_ids"]
    matches = [finding for finding in report["findings"]
               if finding.get("rule_id") == row["rule_id"] and finding.get("row_id") == row["row_id"]]
    assert matches, f"Expected governed finding absent for {row['rule_id']} / {row['row_id']}."
    assert any(f["data_location"] == row["xml_path_context"] for f in matches)
    assert report["passed"] is False
    page.goto(f"{url}/validation/?run_id={report['run_id']}")
    download_same_report(page, report, tmp_path)
    assert len(calls) == 1 and path.read_bytes() == payload


def test_it_46_r4_s1_conditional_required_fixture_in_result_and_download(
    workflow_server, page, tmp_path, record_property,
):
    record_property("scenario_id", "IT-46R4S1")
    url, _manifest, calls = workflow_server
    # Reuse the established conditional inventory and its derived XML.
    from rdflib import Graph, Namespace, URIRef
    from lxml import etree
    vocabulary = Namespace("urn:uad36:test-suite:vocab:")
    inventory = Graph().parse(CORPUS.parent / "single_equality/test-suite.ttl", format="turtle")
    case = URIRef("urn:uad36:test-case:IT-1R2S1:UAD1022")
    def value(predicate):
        values = list(inventory.objects(case, vocabulary[predicate]))
        assert len(values) == 1
        return str(values[0])
    path = ROOT / value("baselinePath")
    original = path.read_bytes()
    tree = etree.fromstring(original, etree.XMLParser(resolve_entities=False, no_network=True))
    trigger = tree.xpath(value("triggerXPath"), namespaces=NAMESPACES)
    assert len(trigger) == 1
    trigger[0].text = "Other"
    for element in tree.xpath(value("dependentXPath"), namespaces=NAMESPACES):
        element.getparent().remove(element)
    payload = etree.tostring(tree, encoding="utf-8", xml_declaration=True)
    response = page.request.post(f"{url}/validate/uad36", data={
        "package_name": "UAD1022-matching-missing.xml", "xml_text": payload.decode("utf-8"), "investor_scope": "both",
    })
    assert response.status == 200, response.text()
    report = response.json()
    assert_recorded_coverage(report, payload)
    matches = [f for f in report["findings"] if f.get("rule_id") == "UAD1022"]
    assert len(matches) == 1
    assert matches[0]["row_id"] == "0100.0053"
    assert matches[0]["data_location"] == value("expectedDataLocation")
    assert "UAD1022" in report["coverage"]["evaluated_rule_ids"]
    page.goto(f"{url}/validation/?run_id={report['run_id']}")
    download_same_report(page, report, tmp_path)
    assert len(calls) == 1 and path.read_bytes() == original


@pytest.mark.parametrize("problem", ["malformed-xml", "evaluation-failure"])
def test_it_46_r4_s1_browser_reports_failure_and_supports_recovery(
    problem, workflow_server, page, tmp_path, monkeypatch, record_property,
):
    record_property("scenario_id", "IT-46R4S1")
    url, manifest, calls = workflow_server
    source, baseline = baseline_bytes(manifest)
    page.goto(f"{url}/validation/")
    with monkeypatch.context() as fault:
        if problem == "evaluation-failure":
            validation = importlib.import_module("app.services.validation")
            def unavailable(*args, **kwargs):
                raise RuntimeError("IT-46R4S1 controlled business evaluator unavailable")
            fault.setattr(validation, "evaluate_required_data", unavailable)
        payload = b'<MESSAGE><ADDRESS></MESSAGE>' if problem == "malformed-xml" else baseline
        report = browser_submit(page, url, f"{problem}.xml", payload)
    assert report["passed"] is False and report["coverage"]["complete"] is False
    assert report["processing_status"] in {"failed", "incomplete"}
    assert report["failure"]["message"] and report["failure"]["suggested_action"]
    assert report["coverage"]["not_evaluated"]
    result = download_same_report(page, report, tmp_path)
    expect(result).to_contain_text(re.compile(r"incomplete|failed", re.I))
    expect(result).to_contain_text(report["failure"]["message"])
    expect(result).to_contain_text(report["failure"]["suggested_action"])
    recovered = browser_submit(page, url, "corrected-or-retried.xml", baseline)
    assert recovered["run_id"] != report["run_id"]
    assert recovered["passed"] is True and recovered["processing_status"] == "completed"
    download_same_report(page, recovered, tmp_path)
    assert len(calls) == 2 and source.read_bytes() == baseline
