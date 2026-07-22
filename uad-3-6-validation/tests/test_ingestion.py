from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_supports_uad36():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["uad_version"] == "3.6"


def test_load_gse_trimmed_schema_into_graph_store():
    response = client.post(
        "/ingest/schema",
        json={"schema_name": "UAD36TrimmedSchema", "schema_version": "UAD 3.6"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["message"] == "Schema assets ingested"
    resource_types = {item["resource_type"] for item in body["resources_created"]}
    assert "schema_element" in resource_types
    assert "datatype" in resource_types
    assert "controlled_value" in resource_types
    assert body["provenance"]["source_version"] == "UAD 3.6"


def test_load_appendix_a_mapping_and_xlink_requirements():
    response = client.post("/ingest/mappings", json={})
    assert response.status_code == 200
    body = response.json()
    assert body["message"] == "Appendix A mapping assets ingested"
    assert body["resources_created"][0]["resource_type"] == "xlink_predicate"
    assert body["resources_created"][0]["iri"].startswith("https://example.org/uad36/relationship/")
    assert body["provenance"]["source_section"] == "Appendix A"


def test_load_appendix_h_rules():
    response = client.post("/ingest/rules", json={})
    assert response.status_code == 200
    body = response.json()
    assert body["message"] == "Appendix H rules ingested"
    rule = body["rules_created"][0]
    assert rule["rule_id"] == "UAD36-AH-PLACEHOLDER-001"
    assert rule["applies_to"] == "both"
    assert rule["provenance"]["source_section"] == "Appendix H"


def test_preserve_source_provenance_when_resource_is_queried():
    client.post("/ingest/schema", json={"schema_name": "UAD36TrimmedSchema"})
    response = client.get("/resources/schema:root")
    assert response.status_code == 200
    body = response.json()
    assert body["provenance"]["source_document"] == "GSE trimmed UAD 3.6 schema"
    assert body["provenance"]["source_section"] == "schema"
    assert "ingestion_timestamp" in body["provenance"]
