"""IT-52R3S1: reject a constraint when no Logical Schema resource can be resolved."""

from __future__ import annotations

from uuid import uuid4

import pytest
from rdflib import Graph, Literal, Namespace, RDF, URIRef

from app.services.construction_exchange import UADEX
from app.services.logical_schema_binding_agent import (
    bind_normalized_constraint_to_logical_schema,
)


CONSTRAINT_VOCAB = Namespace(
    "https://dynamicontology.com/uad36/constraint-vocabulary#"
)
LOGICAL_SCHEMA = Namespace(
    "https://dynamicontology.com/uad36/logical-schema#"
)
LOGICAL_SCHEMA_MODEL = URIRef(
    "https://dynamicontology.com/uad36/logical-schema/model"
)


def test_it_52_r3_s1_rejects_constraint_without_resolvable_schema_resource() -> None:
    """A valid model with no matching element must not produce a binding."""
    token = uuid4().hex
    requested_name = f"UnmatchedDataPoint{token}"
    unrelated_name = f"DifferentDataPoint{token}"

    constraint_id = URIRef(
        f"https://dynamicontology.com/uad36/constraint/it52r3s1/{token}"
    )
    schema_resource_id = URIRef(
        f"https://dynamicontology.com/uad36/logical-schema/"
        f"element/{token}"
    )
    schema_name_id = URIRef(
        f"https://dynamicontology.com/uad36/logical-schema/"
        f"qname/{token}"
    )
    schema_elements_id = URIRef(
        f"https://dynamicontology.com/uad36/logical-schema/"
        f"collection/elements/{token}"
    )

    normalized_graph = Graph()
    normalized_graph.add(
        (
            constraint_id,
            RDF.type,
            CONSTRAINT_VOCAB.NormalizedConstraint,
        )
    )
    normalized_graph.add(
        (
            constraint_id,
            CONSTRAINT_VOCAB.dataPointName,
            Literal(requested_name),
        )
    )

    logical_schema_graph = Graph()
    logical_schema_graph.add(
        (
            LOGICAL_SCHEMA_MODEL,
            RDF.type,
            LOGICAL_SCHEMA.SchemaModel,
        )
    )
    logical_schema_graph.add(
        (
            LOGICAL_SCHEMA_MODEL,
            LOGICAL_SCHEMA.elements,
            schema_elements_id,
        )
    )
    logical_schema_graph.add(
        (
            schema_elements_id,
            RDF.type,
            LOGICAL_SCHEMA.Collection,
        )
    )
    logical_schema_graph.add(
        (
            schema_elements_id,
            LOGICAL_SCHEMA.member,
            schema_resource_id,
        )
    )
    logical_schema_graph.add(
        (
            schema_resource_id,
            RDF.type,
            LOGICAL_SCHEMA.ElementDeclaration,
        )
    )
    logical_schema_graph.add(
        (
            schema_resource_id,
            LOGICAL_SCHEMA.name,
            schema_name_id,
        )
    )
    logical_schema_graph.add(
        (
            schema_name_id,
            RDF.type,
            LOGICAL_SCHEMA.QName,
        )
    )
    logical_schema_graph.add(
        (
            schema_name_id,
            LOGICAL_SCHEMA.local_name,
            Literal(unrelated_name),
        )
    )

    output_graph = Graph()

    with pytest.raises(ValueError):
        bind_normalized_constraint_to_logical_schema(
            normalized_graph=normalized_graph,
            logical_schema_graph=logical_schema_graph,
            constraint_id=str(constraint_id),
            output_graph=output_graph,
        )

    assert not set(
        output_graph.objects(
            constraint_id,
            CONSTRAINT_VOCAB.boundLogicalSchemaResource,
        )
    ), "A constraint with no matching schema resource must not be bound."

    assert not any(
        output_graph.subjects(RDF.type, UADEX.ConstructionStageResult)
    ), "A rejected binding must not be recorded as a successful stage result."