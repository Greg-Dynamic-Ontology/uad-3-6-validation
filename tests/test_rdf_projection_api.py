"""API acceptance tests for the RDF Projection stage."""

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_rdf_projection_uses_one_uploaded_appraisal() -> None:
    """Feature: IT-4R1S2

    One uploaded appraisal supplies the RDF Projection stage. The request
    contains one file, and no second selection or upload is performed.
    """

    xml_bytes = b"""<?xml version="1.0" encoding="UTF-8"?>
<uad:MESSAGE xmlns:uad="https://example.com/uad#" />
"""

    response = client.post(
        "/validate/uad36/rdf-projection",
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
    assert report["status"] == "completed"
    assert report["triple_count"] == 1
