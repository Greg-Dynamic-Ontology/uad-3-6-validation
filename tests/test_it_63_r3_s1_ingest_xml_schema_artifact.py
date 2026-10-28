"""IT-63R3S1: ingest and retrieve a schema resource independently of UAD."""

from hashlib import sha256
from urllib.parse import quote
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


def test_it_63_r3_s1_ingests_and_retrieves_non_uad_xml_schema_artifact() -> None:
    token = uuid4().hex
    namespace = f"urn:test:catalog:{token}"
    schema_text = (
        '<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema" '
        f'targetNamespace="{namespace}" elementFormDefault="qualified">'
        '<xs:element name="CatalogTitle" type="xs:string"/>'
        '</xs:schema>'
    )
    provenance = {
        "source_document": f"urn:test:it63r3s1:catalog-schema:{token}",
        "source_version": "Catalog schema version 1",
        "source_section": "Catalog document definitions",
    }
    request = {
        "schema_name": f"Catalog schema {token}",
        "schema_version": provenance["source_version"],
        "source_document": provenance["source_document"],
        "source_section": provenance["source_section"],
        "raw_text": schema_text,
    }

    # This scenario exercises the application API and store through HTTP
    # routes. The live-network boundary is covered separately by IT-63R2.
    with TestClient(app, follow_redirects=False) as client:
        response = client.post("/ingest/schema", json=request)
        assert 200 <= response.status_code < 300, (
            "IT-63R3S1 requires ingestion of a supported non-UAD schema; "
            f"received HTTP {response.status_code}: {response.text}"
        )
        ingestion = response.json()
        resource_id = ingestion.get("candidate_id")
        assert isinstance(resource_id, str) and resource_id.strip(), (
            "Schema ingestion must identify the resource recorded for the artifact."
        )
        created = ingestion.get("resources_created")
        assert isinstance(created, list)
        matching = [resource for resource in created if resource.get("resource_id") == resource_id]
        assert len(matching) == 1, "The identified schema resource must be among created resources."
        identified = matching[0]
        assert isinstance(identified.get("iri"), str) and identified["iri"]

        retrieved = client.get("/resources/" + quote(resource_id, safe=""))
        assert retrieved.status_code == 200, (
            "The returned schema identity must support subsequent resource retrieval."
        )
        resource = retrieved.json()
        assert resource["resource_id"] == resource_id
        assert resource["iri"] == identified["iri"]
        assert resource["label"] == request["schema_name"]
        assert resource["resource_type"] == "xml_schema_candidate"
        assert resource["raw_text"] == schema_text
        assert resource["content_sha256"] == sha256(schema_text.encode("utf-8")).hexdigest()

        for result in (ingestion, identified, resource):
            recorded = result.get("provenance")
            assert isinstance(recorded, dict)
            for field, expected in provenance.items():
                assert recorded.get(field) == expected, (
                    f"Schema resource must retain the supplied provenance field {field}."
                )
        assert resource["provenance"] == identified["provenance"]

        # Retrieval is repeatable and retains the same recorded identity.
        repeated = client.get("/resources/" + quote(resource_id, safe=""))
        assert repeated.status_code == 200
        assert repeated.json() == resource
