"""Tests for persistent Logical Schema Model serialization."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path, PurePosixPath, PureWindowsPath

import pytest
from rdflib import Graph, RDF, URIRef

from app.services.generate_logical_schema_graph import (
    generate_logical_schema_graph,
)
from app.services.logical_schema_serializer import (
    LOGICAL_SCHEMA,
    LOGICAL_SCHEMA_MODEL_IRI,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]

CANONICAL_LOGICAL_SCHEMA_GRAPH = (
    PROJECT_ROOT
    / "docs"
    / "milestones"
    / "milestone-1"
    / "artifacts"
    / "logical-schema.ttl"
)

MINIMAL_SCHEMA = """<?xml version="1.0" encoding="UTF-8"?>
<xs:schema
    xmlns:xs="http://www.w3.org/2001/XMLSchema"
    targetNamespace="urn:uad:test:canonical-artifact"
>
  <xs:complexType name="ExampleType">
    <xs:sequence/>
  </xs:complexType>
</xs:schema>
"""


def _file_digest(path: Path) -> str:
    """Return a stable digest without changing the file."""

    return sha256(path.read_bytes()).hexdigest()


def _parse_graph(path: Path) -> Graph:
    """Parse one Turtle artifact into an RDF graph."""

    graph = Graph()
    graph.parse(path, format="turtle")
    return graph


def _assert_logical_schema_model(graph: Graph) -> None:
    """Require the serialized graph to identify its model root."""

    assert (
        LOGICAL_SCHEMA_MODEL_IRI,
        RDF.type,
        LOGICAL_SCHEMA.SchemaModel,
    ) in graph


def _generate_minimal_graph(tmp_path: Path) -> Graph:
    """Generate a small Logical Schema graph entirely under tmp_path."""

    schema_path = tmp_path / "minimal.xsd"
    schema_path.write_text(MINIMAL_SCHEMA, encoding="utf-8")
    output_path = tmp_path / "logical-schema.ttl"

    generated_file = generate_logical_schema_graph(
        schema_path=schema_path,
        output_file=output_path,
    )

    assert generated_file == output_path
    assert output_path.is_file()
    return _parse_graph(output_path)


def test_serializer_uses_temporary_output_without_modifying_canonical(
    tmp_path: Path,
) -> None:
    """Routine serialization testing must remain fast and repository-safe."""

    assert CANONICAL_LOGICAL_SCHEMA_GRAPH.is_file(), (
        "Canonical Logical Schema artifact does not exist: "
        f"{CANONICAL_LOGICAL_SCHEMA_GRAPH}"
    )
    canonical_digest_before = _file_digest(
        CANONICAL_LOGICAL_SCHEMA_GRAPH
    )

    _assert_logical_schema_model(_generate_minimal_graph(tmp_path))

    assert _file_digest(CANONICAL_LOGICAL_SCHEMA_GRAPH) == (
        canonical_digest_before
    ), "Routine serialization testing modified the canonical artifact."


def test_serialized_source_document_references_are_portable(
    tmp_path: Path,
) -> None:
    """RDF source references must not reveal a machine installation path."""

    graph = _generate_minimal_graph(tmp_path)
    source_references = tuple(
        graph.objects(predicate=LOGICAL_SCHEMA.source_document)
    )

    assert source_references, (
        "The serialized model must retain source-document traceability."
    )

    for source_reference in source_references:
        if isinstance(source_reference, URIRef):
            continue

        reference = str(source_reference)
        assert not PureWindowsPath(reference).is_absolute(), (
            "source_document must be project-relative or a governed IRI; "
            f"found absolute Windows path {reference!r}."
        )
        assert not PurePosixPath(reference).is_absolute(), (
            "source_document must be project-relative or a governed IRI; "
            f"found absolute POSIX path {reference!r}."
        )
        assert "\\" not in reference, (
            "Portable source_document references must use '/' separators; "
            f"found {reference!r}."
        )
        assert str(tmp_path) not in reference, (
            "source_document exposed the test machine directory: "
            f"{reference!r}."
        )


@pytest.mark.canonical_artifact
def test_complete_uad_graph_matches_canonical_artifact(
    tmp_path: Path,
) -> None:
    """Explicit verification reconciles the complete model and snapshot."""

    assert CANONICAL_LOGICAL_SCHEMA_GRAPH.is_file(), (
        "Canonical Logical Schema artifact does not exist: "
        f"{CANONICAL_LOGICAL_SCHEMA_GRAPH}"
    )
    canonical_digest_before = _file_digest(
        CANONICAL_LOGICAL_SCHEMA_GRAPH
    )

    generated_output = tmp_path / "logical-schema.ttl"
    generate_logical_schema_graph(output_file=generated_output)

    canonical_graph = _parse_graph(CANONICAL_LOGICAL_SCHEMA_GRAPH)
    generated_graph = _parse_graph(generated_output)
    _assert_logical_schema_model(generated_graph)

    canonical_triples = set(canonical_graph)
    generated_triples = set(generated_graph)

    assert generated_triples == canonical_triples, (
        "Canonical Logical Schema artifact is stale: "
        f"{len(generated_triples - canonical_triples)} generated triples "
        "are missing from the canonical artifact and "
        f"{len(canonical_triples - generated_triples)} canonical triples "
        "are not produced by the current model."
    )

    assert _file_digest(CANONICAL_LOGICAL_SCHEMA_GRAPH) == (
        canonical_digest_before
    ), "Comprehensive verification modified the canonical artifact."
