"""Acceptance test for reusing a previously loaded appraisal."""

from rdflib import Graph

from app.models.appraisal import LoadedAppraisal
from app.services.rdf_projection import RdfProjectionStage


class RecordingProjector:
    """Record projection inputs while returning a known graph."""

    def __init__(self) -> None:
        self.graph = Graph()
        self.calls: list[tuple[bytes, str]] = []

    def project(
        self,
        *,
        xml_bytes: bytes,
        source_name: str,
    ) -> Graph:
        self.calls.append((xml_bytes, source_name))
        return self.graph


def test_rdf_projection_uses_previously_loaded_appraisal() -> None:
    """Feature: IT-4R1S2

    The RDF Projection stage reuses the loaded appraisal and therefore does
    not require another filename, path, upload, or file-selection operation.
    """

    xml_bytes = b"""<?xml version="1.0" encoding="UTF-8"?>
<uad:MESSAGE xmlns:uad="https://example.com/uad#" />
"""
    loaded_appraisal = LoadedAppraisal(
        source_name="appraisal.xml",
        xml_bytes=xml_bytes,
    )
    projector = RecordingProjector()

    graph = RdfProjectionStage(projector=projector).run(
        loaded_appraisal=loaded_appraisal,
    )

    assert projector.calls == [(xml_bytes, "appraisal.xml")]
    assert graph is projector.graph
