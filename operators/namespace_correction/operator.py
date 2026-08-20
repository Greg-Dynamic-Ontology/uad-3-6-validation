"""Apply the governed namespace correction to an RDF graph."""

from __future__ import annotations

import re

from rdflib import Graph, URIRef
from rdflib.term import Node


PROVISIONAL_SCHEMA_SOURCE_NAMESPACE = (
    "https://dynamicontology.com/owb/schema-source/sha256/"
)
GOVERNED_SCHEMA_SOURCE_NAMESPACE = (
    "https://dynamicontology.com/uad36/source/sha256/"
)

_PROVISIONAL_SCHEMA_SOURCE_PATTERN = re.compile(
    "^"
    + re.escape(PROVISIONAL_SCHEMA_SOURCE_NAMESPACE)
    + r"(?P<digest>[0-9a-f]{64})$"
)


def _correct_schema_source_term(term: Node) -> Node:
    """Return the governed identity for a valid provisional IRI."""

    if not isinstance(term, URIRef):
        return term

    match = _PROVISIONAL_SCHEMA_SOURCE_PATTERN.fullmatch(str(term))
    if match is None:
        return term

    return URIRef(
        GOVERNED_SCHEMA_SOURCE_NAMESPACE + match.group("digest")
    )


def apply(kg_in: Graph) -> Graph:
    """Return a graph with provisional schema-source IRIs corrected."""

    if not isinstance(kg_in, Graph):
        raise TypeError("kg_in must be an rdflib.Graph")

    kg_out = Graph()

    for prefix, namespace in kg_in.namespaces():
        kg_out.bind(prefix, namespace)

    for subject, predicate, object_ in kg_in:
        kg_out.add(
            (
                _correct_schema_source_term(subject),
                _correct_schema_source_term(predicate),
                _correct_schema_source_term(object_),
            )
        )

    return kg_out


__all__ = [
    "GOVERNED_SCHEMA_SOURCE_NAMESPACE",
    "PROVISIONAL_SCHEMA_SOURCE_NAMESPACE",
    "apply",
]
