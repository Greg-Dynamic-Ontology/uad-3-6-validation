"""Complete-graph acceptance test for namespace correction."""

from __future__ import annotations

from pathlib import Path

import app
import pytest
from rdflib import Graph, URIRef
from rdflib.term import Node

from operators.namespace_correction.operator import (
    GOVERNED_SCHEMA_SOURCE_NAMESPACE,
    PROVISIONAL_SCHEMA_SOURCE_NAMESPACE,
    apply,
)


PROJECT_ROOT = Path(app.__file__).resolve().parents[1]
COMPLETE_LOGICAL_SCHEMA_GRAPH = (
    PROJECT_ROOT
    / "docs"
    / "milestones"
    / "milestone-1"
    / "artifacts"
    / "logical-schema.ttl"
)


def _terms_under_namespace(
    graph: Graph,
    namespace: str,
) -> set[URIRef]:
    """Return all graph IRIs governed by one namespace prefix."""

    return {
        term
        for triple in graph
        for term in triple
        if isinstance(term, URIRef)
        and str(term).startswith(namespace)
    }


def _governed_counterpart(term: Node) -> Node:
    """Map one provisional term to its governed counterpart."""

    if not isinstance(term, URIRef):
        return term

    value = str(term)
    if not value.startswith(PROVISIONAL_SCHEMA_SOURCE_NAMESPACE):
        return term

    digest = value.removeprefix(
        PROVISIONAL_SCHEMA_SOURCE_NAMESPACE
    )
    return URIRef(GOVERNED_SCHEMA_SOURCE_NAMESPACE + digest)


@pytest.mark.canonical_artifact
def test_complete_logical_schema_graph_is_namespace_corrected() -> None:
    """IT-9R2S3: Correct the complete Milestone 1 graph."""

    assert COMPLETE_LOGICAL_SCHEMA_GRAPH.is_file(), (
        "IT-9R2S3 requires the complete Milestone 1 Logical Schema "
        f"graph at {COMPLETE_LOGICAL_SCHEMA_GRAPH}."
    )

    kg_in = Graph()
    kg_in.parse(COMPLETE_LOGICAL_SCHEMA_GRAPH, format="turtle")

    provisional_input = _terms_under_namespace(
        kg_in,
        PROVISIONAL_SCHEMA_SOURCE_NAMESPACE,
    )
    governed_input = _terms_under_namespace(
        kg_in,
        GOVERNED_SCHEMA_SOURCE_NAMESPACE,
    )

    assert provisional_input, (
        "IT-9R2S3 requires a non-empty set of provisional "
        "schema-source IRIs in the complete input graph."
    )

    expected_mapped_sources = {
        URIRef(
            GOVERNED_SCHEMA_SOURCE_NAMESPACE
            + str(source).removeprefix(
                PROVISIONAL_SCHEMA_SOURCE_NAMESPACE
            )
        )
        for source in provisional_input
    }
    expected_corrected_triples = {
        tuple(_governed_counterpart(term) for term in triple)
        for triple in kg_in
        if any(term in provisional_input for term in triple)
    }

    kg_out = apply(kg_in)

    governed_output = _terms_under_namespace(
        kg_out,
        GOVERNED_SCHEMA_SOURCE_NAMESPACE,
    )
    provisional_output = _terms_under_namespace(
        kg_out,
        PROVISIONAL_SCHEMA_SOURCE_NAMESPACE,
    )

    assert governed_output == (
        governed_input | expected_mapped_sources
    )
    assert expected_corrected_triples <= set(kg_out)
    assert not provisional_output
