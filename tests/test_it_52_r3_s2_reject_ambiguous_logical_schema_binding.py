"""IT-52R3S2: reject a constraint when multiple schema bindings are possible."""

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


def test_it_52_r3_s2_rejects_ambiguous_logical_schema_binding() -> None:
    """The binder must not choose between same-named elements in two namespaces."""
    token = uuid4().hex
    data_point_name = f"AmbiguousDataPoint{token}"

    constraint_id = URIRef(
        f"https://dynamicontology.com/uad36/constraint/it52r3s2/{token}"
    )
    schema_elements_id = URIRef(
        f"https://dynamicontology.com/uad36/logical-schema/"
        f"collection/elements/{token}"
    )

    schema_resource_ids = (
        URIRef(
            f"https://dynamicontology.com/uad36/logical-schema/"
            f"element/first/{token}"
        ),
        URIRef(
            f"https://dynamicontology.com/uad36/logical-schema/"
            f"element/second/{token}"
        ),
    )
    schema_name_ids = (
        URIRef(
            f"https://dynamicontology.com/uad36/logical-schema/"
            f"qname/first/{token}"
        ),
        URIRef(
            f"https://dynamicontology.com/uad36/logical-schema/"
            f"qname/second/{token}"
        ),
    )
    schema_namespaces = (
        f"urn:it52r3s2:first:{token}",
        f"urn:it52r3s2:second:{token}",
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

    for schema_resource_id, schema_name_id, namespace in zip(
        schema_resource_ids,
        schema_name_ids,
        schema_namespaces,
    ):
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
        logical_schema_graph.add(
            (
                schema_name_id,
                LOGICAL_SCHEMA.namespace,
                Literal(namespace),
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
    ), "An ambiguous constraint must not be bound to either schema resource."

    assert not any(
        output_graph.subjects(RDF.type, UADEX.ConstructionStageResult)
    ), "An ambiguous binding must not be recorded as a successful stage result."