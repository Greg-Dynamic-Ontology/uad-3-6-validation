"""IT-46R3S1: correcting one defect creates a fresh browser validation run.

Two real XML defects are introduced in memory; the correction restores one
original baseline value and leaves the other defect unchanged. The existing
IT-46 XML manifest supplies the historical clock and input digest. Real API,
validators, browser upload, and JSON downloads are used. Only authentication
setup and the historical clock are controlled. No app code is modified.
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


@pytest.fixture
def corrected_upload_server(monkeypatch, page):
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
        assert server.started, "IT-46R3S1 setup: local test server did not start."
        page.context.add_cookies([{
            "name": "wos_session", "value": "it46-review-session",
            "url": url, "httpOnly": True, "sameSite": "Lax",
        }])
        yield url, manifest, calls
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        server_socket.close()



def appraisal_with_missing_fields(baseline, omitted):
    tree = ET.fromstring(baseline)
    address = tree.find(".//m:VALUATION_ANALYSIS/m:PROPERTIES/"
                        "m:PROPERTY[@ValuationUseType='SubjectProperty']/m:ADDRESS", NAMESPACES)
    assert address is not None
    for name in omitted:
        element = address.find(f"m:{name}", NAMESPACES)
        assert element is not None and element.text and element.text.strip()
        address.remove(element)
    return ET.tostring(tree, encoding="utf-8", xml_declaration=True)


def download_report(page, result, destination):
    with page.expect_download() as pending:
        result.get_by_role("link", name=re.compile(r"download.*report", re.I)).click()
    download = pending.value
    assert download.failure() is None
    download.save_as(str(destination))
    return json.loads(destination.read_text(encoding="utf-8-sig"))


@pytest.mark.parametrize("corrected_element,removed_rule,remaining_rule", [
    ("AddressLineText", "UAD1001", "UAD1002"),
    ("CityName", "UAD1002", "UAD1001"),
], ids=["correct-address-retain-city", "correct-city-retain-address"])
def test_it_46_r3_s1_validates_corrected_browser_upload_as_a_new_run(
    corrected_element, removed_rule, remaining_rule,
    corrected_upload_server, page, tmp_path, record_property,
):
    record_property("scenario_id", "IT-46R3S1")
    url, manifest, calls = corrected_upload_server
    case = next(item for item in manifest["cases"] if item["id"] == "schema-valid-baseline")
    source = FIXTURES / case["file"]
    baseline = source.read_bytes()
    assert sha256(baseline).hexdigest() == case["sha256"]
    defects = {"AddressLineText", "CityName"}
    original_upload = appraisal_with_missing_fields(baseline, defects)
    corrected_upload = appraisal_with_missing_fields(baseline, defects - {corrected_element})
    assert original_upload != corrected_upload
    original_name = "SF1-two-reported-defects.xml"
    corrected_name = f"SF1-corrected-{corrected_element}.xml"

    # Given an existing real governed result; the correction itself must pass
    # through the customer's browser file control and request, not this helper.
    response = page.request.post(f"{url}/validate/uad36", data={
        "package_name": original_name, "xml_text": original_upload.decode("utf-8"),
        "investor_scope": "both",
    })
    assert response.status == 200, response.text()
    earlier = response.json()
    assert earlier["schema"]["schema_valid"] is True
    assert earlier["coverage"]["complete"] is True
    assert {f["rule_id"] for f in earlier["findings"]} == {removed_rule, remaining_rule}
    assert len(earlier["findings"]) == 2
    assert earlier["source_sha256"] == sha256(original_upload).hexdigest()
    assert calls == [(original_name, sha256(original_upload).hexdigest())]
    page.goto(f"{url}/validation/?run_id={earlier['run_id']}")
    old_result = page.locator(f'[data-validation-run-id="{earlier["run_id"]}"]')
    expect(old_result).to_be_visible()
    for finding in earlier["findings"]:
        expect(old_result.locator(f'[data-finding-id="{finding["finding_id"]}"]')).to_be_visible()
    exported_earlier = download_report(page, old_result, tmp_path / "earlier-report.json")
    assert exported_earlier == earlier

    # Select a real corrected file via Playwright's native file-input support.
    # No hidden developer controls are forced, no fetch call is injected,
    # and no network request or response is replaced.
    page.locator("#appraisal-file").set_input_files({
        "name": corrected_name, "mimeType": "application/xml", "buffer": corrected_upload,
    })
    with page.expect_response(lambda reply:
        reply.request.method == "POST" and "/validate/uad36" in reply.url
    ) as pending:
        page.locator("#validate-button").click()
    corrected_response = pending.value
    assert corrected_response.url == f"{url}/validate/uad36", (
        "IT-46R3S1 requires the corrected browser upload to execute integrated "
        "schema and governed business validation as a new run. The customer "
        f"upload submitted to {corrected_response.url}; projection-only or "
        "schema-only processing cannot confirm removal of the governed finding."
    )
    assert corrected_response.status == 200, corrected_response.text()
    current = corrected_response.json()
    assert current["run_id"] != earlier["run_id"]
    assert current["package_name"] == corrected_name
    assert current["source_sha256"] == sha256(corrected_upload).hexdigest()
    assert current["source_sha256"] != earlier["source_sha256"]
    assert current["processing_status"] == "completed"
    assert current["schema"]["schema_valid"] is True
    assert current["coverage"]["complete"] is True
    assert current["coverage"]["not_evaluated"] == []
    assert current["coverage"]["constraint_set"] == earlier["coverage"]["constraint_set"]
    assert current["schema"]["sha256"] == earlier["schema"]["sha256"]
    assert current["failure"] is None
    assert current["passed"] is False, "The remaining defect must still prevent passing."
    assert removed_rule in current["coverage"]["evaluated_rule_ids"], "Absence due to skipped evaluation is not a correction."
    assert remaining_rule in current["coverage"]["evaluated_rule_ids"]
    assert len(current["findings"]) == 1
    assert {finding["rule_id"] for finding in current["findings"]} == {remaining_rule}
    old_remaining = next(f for f in earlier["findings"] if f["rule_id"] == remaining_rule)
    new_remaining = current["findings"][0]
    for field in ("rule_id", "row_id", "severity", "data_location", "expected_condition", "finding"):
        assert new_remaining[field] == old_remaining[field]
    assert {f["finding_id"] for f in earlier["findings"]}.isdisjoint(
        f["finding_id"] for f in current["findings"]
    ), "An earlier finding identity was carried into the new run."

    new_result = page.locator(f'[data-validation-run-id="{current["run_id"]}"]')
    expect(new_result).to_be_visible()
    expect(new_result).to_contain_text(corrected_name)
    expect(new_result).to_contain_text(current["source_sha256"])
    expect(new_result.locator("[data-finding-id]")).to_have_count(1)
    expect(new_result.locator(f'[data-finding-id="{new_remaining["finding_id"]}"]')).to_contain_text(remaining_rule)
    for old_finding in earlier["findings"]:
        expect(page.locator(f'[data-finding-id="{old_finding["finding_id"]}"]')).to_have_count(0)
    exported_current = download_report(page, new_result, tmp_path / "corrected-report.json")
    assert exported_current == current
    assert exported_current["run_id"] != exported_earlier["run_id"]
    assert exported_current["source_sha256"] != exported_earlier["source_sha256"]
    for report in (earlier, current):
        saved = page.request.get(f"{url}/validation-runs/{report['run_id']}")
        assert saved.status == 200 and saved.json() == report
    assert calls == [
        (original_name, sha256(original_upload).hexdigest()),
        (corrected_name, sha256(corrected_upload).hexdigest()),
    ], "Review and download must not create extra runs."
    assert source.read_bytes() == baseline
