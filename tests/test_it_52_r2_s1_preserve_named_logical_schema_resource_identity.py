"""IT-52R2S1: preserve a named Logical Schema resource identity during binding."""

from __future__ import annotations

from uuid import uuid4

from rdflib import Graph, Literal, Namespace, RDF, URIRef

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


def test_it_52_r2_s1_preserves_named_logical_schema_resource_identity() -> None:
    """Binding refers to the exact named schema resource supplied as input."""
    token = uuid4().hex
    data_point_name = f"IT52R2S1DataPoint{token}"

    constraint_id = URIRef(
        f"https://dynamicontology.com/uad36/constraint/it52r2s1/{token}"
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

    # Exercise the serialized-graph boundary used by construction stages.
    normalized_serialization = normalized_graph.serialize(format="turtle")
    normalized_graph = Graph().parse(
        data=normalized_serialization,
        format="turtle",
    )
    schema_serialization = logical_schema_graph.serialize(format="turtle")
    logical_schema_graph = Graph().parse(
        data=schema_serialization,
        format="turtle",
    )

    output_graph = Graph()
    bind_normalized_constraint_to_logical_schema(
        normalized_graph=normalized_graph,
        logical_schema_graph=logical_schema_graph,
        constraint_id=str(constraint_id),
        output_graph=output_graph,
    )

    binding_predicate = CONSTRAINT_VOCAB.boundLogicalSchemaResource

    assert (
        LOGICAL_SCHEMA_MODEL,
        RDF.type,
        LOGICAL_SCHEMA.SchemaModel,
    ) in logical_schema_graph
    assert (
        schema_elements_id,
        LOGICAL_SCHEMA.member,
        schema_resource_id,
    ) in logical_schema_graph
    assert (
        schema_resource_id,
        RDF.type,
        LOGICAL_SCHEMA.ElementDeclaration,
    ) in logical_schema_graph
    assert (
        constraint_id,
        binding_predicate,
        schema_resource_id,
    ) in output_graph, (
        "Binding must reuse the exact named Logical Schema resource IRI "
        "provided by the governed model."
    )

    bound_resources = set(
        output_graph.objects(constraint_id, binding_predicate)
    )
    assert bound_resources == {schema_resource_id}, (
        "Binding must not mint or substitute a replacement Logical Schema IRI."
    )