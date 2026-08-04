"""Acceptance test for RDF Projection source traceability."""

from hashlib import sha256

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_validation_run_records_rdf_projection_source_traceability() -> None:
    """Feature: IT-4R2S2."""
    xml_bytes = b"""<?xml version="1.0" encoding="UTF-8"?>
<uad:MESSAGE xmlns:uad="https://example.com/uad#" />
"""

    projection_response = client.post(
        "/validate/uad36/pipeline",
        data={"pipeline": "rdf-projection"},
        files={
            "file": (
                "appraisal.xml",
                xml_bytes,
                "application/xml",
            )
        },
    )

    assert projection_response.status_code == 200

    projection_report = projection_response.json()
    run_id = projection_report["run_id"]

    run_response = client.get(f"/validation-runs/{run_id}")

    assert run_response.status_code == 200

    validation_run = run_response.json()

    assert validation_run["run_id"] == run_id
    assert validation_run["artifacts"] == [
        {
            "artifact_type": "rdf-instance-graph",
            "produced_by": "rdf-projection",
            "source": {
                "package_name": "appraisal.xml",
                "sha256": sha256(xml_bytes).hexdigest(),
            },
            "triple_count": 1,
        }
    ]
