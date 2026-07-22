from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_validate_uad36_applies_both_gse_rule_sets_by_default():
    response = client.post(
        "/validate/uad36",
        json={"package_name": "sample.xml", "xml_text": "<APPRAISAL_REPORT/>"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["uad_version"] == "3.6"
    assert body["investor_scope"] == "both"
    assert "run_id" in body
    assert "summary" in body
    assert "findings" in body


def test_validate_fannie_scope():
    response = client.post(
        "/validate/uad36/fannie",
        json={"package_name": "sample.xml", "xml_text": "<APPRAISAL_REPORT/>"},
    )
    assert response.status_code == 200
    assert response.json()["investor_scope"] == "fannie_mae"


def test_validate_freddie_scope():
    response = client.post(
        "/validate/uad36/freddie",
        json={"package_name": "sample.xml", "xml_text": "<APPRAISAL_REPORT/>"},
    )
    assert response.status_code == 200
    assert response.json()["investor_scope"] == "freddie_mac"


def test_invalid_xml_payload_returns_structured_finding():
    response = client.post(
        "/validate/uad36",
        json={"package_name": "bad.xml", "xml_text": "not xml"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["error"] == 1
    finding = body["findings"][0]
    assert finding["rule_type"] == "schema"
    assert finding["data_location"] == "/"
    assert finding["source"]["source_document"] == "GSE trimmed UAD 3.6 schema"


def test_get_validation_run_after_validation():
    validate_response = client.post(
        "/validate/uad36",
        json={"package_name": "bad.xml", "xml_text": "not xml"},
    )
    run_id = validate_response.json()["run_id"]
    response = client.get(f"/validation-runs/{run_id}")
    assert response.status_code == 200
    assert response.json()["run_id"] == run_id


def test_explain_finding_is_advisory():
    validate_response = client.post(
        "/validate/uad36",
        json={"package_name": "bad.xml", "xml_text": "not xml"},
    )
    finding_id = validate_response.json()["findings"][0]["finding_id"]
    response = client.post(f"/explain/finding/{finding_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["finding_id"] == finding_id
    assert body["advisory"] is True
    assert body["authoritative_result_unchanged"] is True


def test_review_revision_history_is_advisory_not_deterministic_failure():
    response = client.post(
        "/review/revision-history",
        json={"revision_history_detail": "Corrected condition rating narrative.", "related_finding_ids": ["F-123"]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["advisory"] is True
    assert body["deterministic_failure"] is False
    assert body["comments"]


def test_xml_schema_upload_reports_malformed_xml() -> None:
    response = client.post(
        "/validate/uad36/xml-schema",
        files={"file": ("malformed.xml", b"<MESSAGE>", "application/xml")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["package_name"] == "malformed.xml"
    assert body["well_formed"] is False
    assert body["schema_valid"] is False
    assert body["status"] == "failed"
    assert body["summary"]["error_count"] >= 1
    assert body["findings"]


def test_xml_schema_upload_reports_well_formed_non_uad_xml() -> None:
    response = client.post(
        "/validate/uad36/xml-schema",
        files={
            "file": (
                "invoice.xml",
                b"<?xml version='1.0'?><Invoice><Identifier>1</Identifier></Invoice>",
                "application/xml",
            )
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["package_name"] == "invoice.xml"
    assert body["well_formed"] is True
    assert body["schema_valid"] is False
    assert body["status"] == "failed"
    assert body["summary"]["error_count"] >= 1
    assert body["findings"]


def test_validation_page_is_served_by_application() -> None:
    response = client.get("/validation/")

    assert response.status_code == 200
    assert "Validate a UAD 3.6 Appraisal" in response.text
    assert "Pipeline Artifacts" in response.text
    assert "../assets/js/validation.js" in response.text
