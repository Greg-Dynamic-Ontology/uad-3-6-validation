"""API acceptance tests for the UI-facing validation pipeline."""

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_pipeline_runs_selected_stage_from_one_uploaded_appraisal() -> None:
    """The UI submits one file and one pipeline choice to Python."""
    xml_bytes = b"""<?xml version="1.0" encoding="UTF-8"?>
<uad:MESSAGE xmlns:uad="https://example.com/uad#" />
"""

    response = client.post(
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

    assert response.status_code == 200

    report = response.json()

    assert report["package_name"] == "appraisal.xml"
    assert report["pipeline"] == "rdf-projection"
    assert report["status"] == "completed"
    assert report["stages"] == [
        {
            "name": "rdf-projection",
            "status": "completed",
            "artifacts": {
                "rdf_triple_count": 1,
            },
        }
    ]
