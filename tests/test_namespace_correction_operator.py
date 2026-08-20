"""Acceptance tests for the namespace-correction graph operator."""

from importlib import import_module

import pytest
from rdflib import Graph, Namespace, URIRef


LOGICAL_SCHEMA = Namespace(
    "https://dynamicontology.com/uad36/logical-schema#"
)
EXAMPLE = Namespace("https://dynamicontology.com/test/")

PROVISIONAL_NAMESPACE = (
    "https://dynamicontology.com/owb/schema-source/sha256/"
)
GOVERNED_NAMESPACE = (
    "https://dynamicontology.com/uad36/source/sha256/"
)

DIGEST = "a" * 64
PROVISIONAL_SOURCE = URIRef(PROVISIONAL_NAMESPACE + DIGEST)
GOVERNED_SOURCE = URIRef(GOVERNED_NAMESPACE + DIGEST)


def _load_operator_module():
    """Load the implementation with a useful red-state failure."""

    try:
        return import_module(
            "operators.namespace_correction.operator"
        )
    except ModuleNotFoundError as error:
        if error.name in {
            "operators",
            "operators.namespace_correction",
            "operators.namespace_correction.operator",
        }:
            pytest.fail(
                "IT-9R2S1 requires the namespace-correction "
                "implementation at "
                "operators/namespace_correction/operator.py."
            )
        raise


def _contains_term(graph: Graph, term: URIRef) -> bool:
    """Return whether a term occurs in any RDF triple position."""

    return any(term in triple for triple in graph)


def test_provisional_schema_source_iri_is_corrected() -> None:
    """IT-9R2S1: Replace one provisional source IRI deliberately."""

    namespace_correction = _load_operator_module()
    assert hasattr(namespace_correction, "apply"), (
        "IT-9R2S1 requires namespace_correction.apply(kg_in)."
    )

    kg_in = Graph()
    kg_in.add(
        (
            EXAMPLE.schemaComponent,
            LOGICAL_SCHEMA.source_document,
            PROVISIONAL_SOURCE,
        )
    )

    kg_out = namespace_correction.apply(kg_in)

    assert isinstance(kg_out, Graph)
    assert (
        EXAMPLE.schemaComponent,
        LOGICAL_SCHEMA.source_document,
        GOVERNED_SOURCE,
    ) in kg_out
    assert str(GOVERNED_SOURCE).removeprefix(
        GOVERNED_NAMESPACE
    ) == DIGEST
    assert not _contains_term(kg_out, PROVISIONAL_SOURCE)


def test_schema_source_iri_is_corrected_in_every_triple_position() -> None:
    """IT-9R2S2: Correct subject, predicate, and object occurrences."""

    namespace_correction = _load_operator_module()
    assert hasattr(namespace_correction, "apply"), (
        "IT-9R2S2 requires namespace_correction.apply(kg_in)."
    )

    kg_in = Graph()
    kg_in.add(
        (
            PROVISIONAL_SOURCE,
            EXAMPLE.subjectPositionPredicate,
            EXAMPLE.subjectPositionObject,
        )
    )
    kg_in.add(
        (
            EXAMPLE.predicatePositionSubject,
            PROVISIONAL_SOURCE,
            EXAMPLE.predicatePositionObject,
        )
    )
    kg_in.add(
        (
            EXAMPLE.objectPositionSubject,
            EXAMPLE.objectPositionPredicate,
            PROVISIONAL_SOURCE,
        )
    )

    kg_out = namespace_correction.apply(kg_in)

    expected_triples = {
        (
            GOVERNED_SOURCE,
            EXAMPLE.subjectPositionPredicate,
            EXAMPLE.subjectPositionObject,
        ),
        (
            EXAMPLE.predicatePositionSubject,
            GOVERNED_SOURCE,
            EXAMPLE.predicatePositionObject,
        ),
        (
            EXAMPLE.objectPositionSubject,
            EXAMPLE.objectPositionPredicate,
            GOVERNED_SOURCE,
        ),
    }

    assert set(kg_out) == expected_triples
    assert not _contains_term(kg_out, PROVISIONAL_SOURCE)
