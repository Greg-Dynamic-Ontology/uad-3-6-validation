"""IT-46R1S1: one customer request joins real XSD and business validation.

Integration boundary: the existing browser's POST /validate/uad36 JSON request,
including its original file text. TestClient exercises the real ASGI app; this
is not the browser smoke test required by IT-46R4S1 or a WorkOS sign-in test.
Only authentication setup, the historical fixture clock, and one deliberate
evaluator outage are controlled. Validators are observed and delegated, not
replaced with passing responses. Finding expectations come from the manifest.
"""
from datetime import date
from hashlib import sha256
import importlib
import json
from pathlib import Path
from xml.etree import ElementTree as ET

from fastapi.testclient import TestClient
from lxml import etree
import pytest

from app.services import required_data
from app.services.gse_constraint_sources import read_active_compliance_workbook_rows
from app.services.xml_schema_validator import UAD36_SCHEMA_PATH, UAD36_SCHEMA_VERSION


ROOT = Path(required_data.__file__).resolve().parents[2]
# The review package has the same fixture layout beneath its own directory.
FIXTURES = Path(__file__).resolve().parent / "fixtures/it_46/r1/s1"
MANIFEST_PATH = FIXTURES / "manifest.json"
MANIFEST = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
CASES = MANIFEST["cases"]
NS = {"m": "http://www.mismo.org/residential/2009/schemas"}
OUTAGE_REASON = "IT-46R1S1 controlled numeric evaluator unavailable"


@pytest.fixture
def integrated_customer_client(monkeypatch):
    main = importlib.import_module("app.main")
    routes = importlib.import_module("app.api.routes")
    validation = importlib.import_module("app.services.validation")
    schema_module = importlib.import_module("app.services.xml_schema_validator")
    chronology = importlib.import_module("app.services.date_chronology_required_data")

    class HistoricalDate(date):
        @classmethod
        def today(cls):
            return cls.fromisoformat(MANIFEST["evaluation_date"])

    monkeypatch.setattr(chronology, "date", HistoricalDate)
    monkeypatch.setenv("WORKOS_CLIENT_ID", "client_it46_integration_setup")
    monkeypatch.setenv("WORKOS_REDIRECT_URI", "http://testserver/auth/callback")
    # Reuse the existing authenticated request boundary without contacting WorkOS.
    monkeypatch.setattr(main, "WorkOSClient", lambda **kwargs: object())
    def authenticated_identity(request, _workos):
        assert request.cookies.get("wos_session") == "it46-integration-session"
        return {"id": "user_it46_integration_setup"}
    monkeypatch.setattr(main, "_authenticated_workos_user", authenticated_identity)
    monkeypatch.setattr(main.app.state, "workos_identity_account_links", {
        "user_it46_integration_setup": "account_it46_integration_setup",
    })
    # Each case gets its own service; existing runs are not cleared or changed.
    monkeypatch.setattr(routes, "validation_service", validation.ValidationService())
    observed = {"schema": [], "business": []}
    real_schema = schema_module.validate_uad36_xml_bytes
    real_business = required_data.evaluate_required_data

    def observe_schema(*, package_name, xml_bytes):
        report = real_schema(package_name=package_name, xml_bytes=xml_bytes)
        observed["schema"].append((package_name, xml_bytes, report))
        return report

    def observe_business(root, investor, **kwargs):
        before = ET.tostring(root)
        findings = real_business(root, investor, **kwargs)
        assert ET.tostring(root) == before, "IT-46R1S1: shared evaluators changed uploaded XML."
        observed["business"].append(findings)
        return findings

    monkeypatch.setattr(schema_module, "validate_uad36_xml_bytes", observe_schema)
    monkeypatch.setattr(routes, "validate_uad36_xml_bytes", observe_schema)
    monkeypatch.setattr(validation, "validate_uad36_xml_bytes", observe_schema, raising=False)
    monkeypatch.setattr(required_data, "evaluate_required_data", observe_business)
    monkeypatch.setattr(validation, "evaluate_required_data", observe_business)
    with TestClient(main.app, raise_server_exceptions=False) as client:
        client.cookies.set("wos_session", "it46-integration-session")
        yield client, observed


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_it_46_r1_s1_validates_readable_uploaded_uad_xml(
    case, integrated_customer_client, monkeypatch, record_property,
):
    record_property("scenario_id", "IT-46R1S1")
    client, observed = integrated_customer_client
    path = FIXTURES / case["file"]
    original = path.read_bytes()
    assert sha256(original).hexdigest() == case["sha256"], "Controlled input digest changed."
    parser = etree.XMLParser(resolve_entities=False, no_network=True)
    tree = etree.fromstring(original, parser)
    assert not tree.getroottree().docinfo.doctype
    governed_schema = etree.XMLSchema(etree.parse(str(UAD36_SCHEMA_PATH), parser))
    assert governed_schema.validate(tree) is case["schema_valid"], (
        f"IT-46R1S1 setup: fixture {case['id']} does not have its declared XSD outcome."
    )
    source = read_active_compliance_workbook_rows(configuration_path=ROOT / "config/configuration.ttl")
    selected = {r["Message ID"] for r in required_data.load_required_rules()}
    assert "UAD1001" in selected

    unavailable = None
    if case.get("evaluator_outage"):
        row = next(r for r in required_data.load_required_rules()
                   if required_data.numeric_bound_binding_for(r) is not None)
        unavailable = row["Message ID"]
        real_numeric = required_data.evaluate_numeric_bound
        def controlled_outage(root, investor, rule):
            if rule["Message ID"] == unavailable:
                raise RuntimeError(OUTAGE_REASON)
            return real_numeric(root, investor, rule)
        monkeypatch.setattr(required_data, "evaluate_numeric_bound", controlled_outage)

    # This is the actual required-data upload request sent by validation.js.
    try:
        response = client.post("/validate/uad36", json={
            "package_name": path.name,
            "xml_text": original.decode("utf-8"),
            "investor_scope": "both",
        })
    finally:
        assert path.read_bytes() == original, "IT-46R1S1: source upload was changed."
    assert response.status_code == 200, (
        "IT-46R1S1 requires a structured integrated result, including incomplete "
        f"checks where safe validation can continue. Received {response.status_code}: {response.text[:400]}"
    )
    report = response.json()
    schema_result = report.get("schema")
    assert isinstance(schema_result, dict), (
        "IT-46R1S1 requires the existing customer validation request to return "
        "its governed XSD assessment alongside business-rule findings. "
        "The current response contains no schema result; separate schema-only "
        "requests do not satisfy this integration scenario."
    )
    assert schema_result["schema_valid"] is case["schema_valid"]
    assert schema_result["schema_version"] == UAD36_SCHEMA_VERSION
    assert schema_result["sha256"] == sha256(UAD36_SCHEMA_PATH.read_bytes()).hexdigest()
    assert isinstance(schema_result["findings"], list)
    assert bool(schema_result["findings"]) is (not case["schema_valid"])
    assert len(observed["schema"]) == 1, "The actual shared XSD validator must execute once."
    assert observed["schema"][0][1] == original, "XSD validation must use the exact upload bytes."
    assert observed["schema"][0][2].schema_valid is case["schema_valid"]
    assert len(observed["business"]) == 1, "The shared business evaluators must execute once."

    findings = report["findings"]
    address = [f for f in findings if f.get("rule_id") == "UAD1001"]
    assert len(address) == case["expected_address_findings"], (
        "A schema defect must not suppress independently evaluable address findings."
    )
    for finding in address:
        row = next(r for r in source.rows if r["Message ID"] == "UAD1001")
        assert finding["row_id"] == "0100.0007"
        assert finding["severity"] == "fatal"
        assert finding["rule_type"] == "appendix_h"
        assert finding["finding"] == row["Message Text"]
        assert finding["data_location"] == case["expected_address_context"]
    assert not any(f.get("rule_type") == "schema" for f in findings), (
        "Schema findings belong to schema assessment, not the business-rule finding list."
    )
    if case["id"] == "schema-valid-baseline":
        assert findings == []

    coverage = report["coverage"]
    assert set(coverage["selected_rule_ids"]) == selected
    evaluated = set(coverage["evaluated_rule_ids"])
    skipped = coverage["not_evaluated"]
    assert isinstance(skipped, list)
    skipped_ids = [item["rule_id"] for item in skipped]
    assert len(skipped_ids) == len(set(skipped_ids))
    assert all(isinstance(item["reason"], str) and item["reason"].strip() for item in skipped)
    assert evaluated.isdisjoint(skipped_ids)
    assert evaluated | set(skipped_ids) == selected
    assert "UAD1001" in evaluated
    if unavailable:
        assert unavailable in skipped_ids and unavailable not in evaluated
        assert any(item["rule_id"] == unavailable and OUTAGE_REASON in item["reason"] for item in skipped)
        assert coverage["complete"] is False
    else:
        assert skipped == [] and coverage["complete"] is True

    constraint_set = coverage["constraint_set"]
    assert constraint_set["version"] == "1.5"
    assert constraint_set["source_document"] == str(source.workbook_path)
    assert constraint_set["source_sheet"] == source.worksheet_name
    assert constraint_set["sha256"] == sha256(source.workbook_path.read_bytes()).hexdigest()
    assert report["package_name"] == path.name
    assert report["source_sha256"] == case["sha256"]
    assert isinstance(report["run_id"], str) and report["run_id"]
    retrieved = client.get(f"/validation-runs/{report['run_id']}")
    assert retrieved.status_code == 200 and retrieved.json() == report
