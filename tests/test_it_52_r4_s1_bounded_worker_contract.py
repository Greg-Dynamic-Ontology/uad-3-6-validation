"""IT-52R4S1: return only contracted output or a contracted exception."""

from __future__ import annotations

from uuid import uuid4

import pytest
from rdflib import Graph, Literal, Namespace, RDF, URIRef

from app.services.construction_exchange import ConstructionStageResultRecord
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


def test_it_52_r4_s1_returns_only_contracted_output_or_exception() -> None:
    """The worker returns its declared result record or raises a ValueError."""
    token = uuid4().hex
    data_point_name = f"IT52R4S1DataPoint{token}"

    constraint_id = URIRef(
        f"https://dynamicontology.com/uad36/constraint/it52r4s1/{token}"
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
            Literal(data_point_name),
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
            Literal(data_point_name),
        )
    )

    successful_output_graph = Graph()
    result = bind_normalized_constraint_to_logical_schema(
        normalized_graph=normalized_graph,
        logical_schema_graph=logical_schema_graph,
        constraint_id=str(constraint_id),
        output_graph=successful_output_graph,
    )

    assert isinstance(result, ConstructionStageResultRecord), (
        "A successful worker call must return the contracted "
        "ConstructionStageResultRecord."
    )

    invalid_constraint_id = URIRef(
        f"https://dynamicontology.com/uad36/constraint/it52r4s1/"
        f"missing-{token}"
    )
    failed_output_graph = Graph()

    with pytest.raises(ValueError):
        bind_normalized_constraint_to_logical_schema(
            normalized_graph=normalized_graph,
            logical_schema_graph=logical_schema_graph,
            constraint_id=str(invalid_constraint_id),
            output_graph=failed_output_graph,
        )

    assert len(failed_output_graph) == 0, (
        "A rejected worker call must not leave partial output in the graph."
    )