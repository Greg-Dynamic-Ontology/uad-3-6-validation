"""Bind normalized governed constraints to Logical Schema resources."""

from __future__ import annotations

from rdflib import Graph, Namespace, RDF, URIRef
from rdflib.namespace import RDFS

from app.services.construction_exchange import (
    UADEX,
    ConstructionStageResultRecord,
    exchange_successful_construction_stage_result,
)


CONSTRAINT_VOCAB = Namespace(
    "https://dynamicontology.com/uad36/constraint-vocabulary#"
)
LOGICAL_SCHEMA = Namespace(
    "https://dynamicontology.com/uad36/logical-schema#"
)
LOGICAL_SCHEMA_MODEL_IRI = URIRef(
    "https://dynamicontology.com/uad36/logical-schema/model"
)


def _require_normalized_constraint(
    normalized_graph: Graph,
    constraint_id: str,
) -> tuple[URIRef, str]:
    """Verify the normalized resource and read its governed data point name."""
    constraint = URIRef(constraint_id)

    if (
        constraint,
        RDF.type,
        CONSTRAINT_VOCAB.NormalizedConstraint,
    ) not in normalized_graph:
        raise ValueError(
            "constraint_id must identify a NormalizedConstraint "
            "in normalized_graph"
        )

    data_point_names = set(
        normalized_graph.objects(
            constraint,
            CONSTRAINT_VOCAB.dataPointName,
        )
    )
    if len(data_point_names) != 1:
        raise ValueError(
            "a normalized constraint must have exactly one dataPointName"
        )

    data_point_name = next(iter(data_point_names))
    if not hasattr(data_point_name, "toPython"):
        raise ValueError("dataPointName must be an RDF literal")

    local_name = str(data_point_name).strip()
    if not local_name:
        raise ValueError("dataPointName must not be blank")

    return constraint, local_name


def _resolve_logical_schema_resource(
    logical_schema_graph: Graph,
    data_point_name: str,
) -> URIRef:
    """Resolve one data point name to its exact Logical Schema declaration."""
    if (
        LOGICAL_SCHEMA_MODEL_IRI,
        RDF.type,
        LOGICAL_SCHEMA.SchemaModel,
    ) not in logical_schema_graph:
        raise ValueError(
            "logical_schema_graph must contain the governed "
            "Logical Schema Model resource"
        )

    matches: set[URIRef] = set()

    for declaration in logical_schema_graph.subjects(
        RDF.type,
        LOGICAL_SCHEMA.ElementDeclaration,
    ):
        if not isinstance(declaration, URIRef):
            continue

        for qname_predicate in (
            LOGICAL_SCHEMA.name,
            LOGICAL_SCHEMA.ref,
        ):
            for qname in logical_schema_graph.objects(
                declaration,
                qname_predicate,
            ):
                if not isinstance(qname, URIRef):
                    continue

                local_names = {
                    str(value).strip()
                    for value in logical_schema_graph.objects(
                        qname,
                        LOGICAL_SCHEMA.local_name,
                    )
                }
                if data_point_name in local_names:
                    matches.add(declaration)

    if not matches:
        raise ValueError(
            "no Logical Schema element declaration matches dataPointName "
            f"{data_point_name!r}"
        )

    if len(matches) != 1:
        raise ValueError(
            "dataPointName must resolve to exactly one Logical Schema "
            f"element declaration; found {len(matches)} for "
            f"{data_point_name!r}"
        )

    return next(iter(matches))


def _copy_graph(source_graph: Graph, destination_graph: Graph) -> None:
    """Copy triples and namespace bindings without replacing existing data."""
    for prefix, namespace in source_graph.namespaces():
        destination_graph.bind(prefix, namespace, replace=False)

    for triple in source_graph:
        destination_graph.add(triple)


def bind_normalized_constraint_to_logical_schema(
    *,
    normalized_graph: Graph,
    logical_schema_graph: Graph,
    constraint_id: str,
    output_graph: Graph,
) -> ConstructionStageResultRecord:
    """Bind a normalized constraint to one governed schema declaration.

    The normalized graph is preserved in output_graph. The constraint is
    linked to the exact Logical Schema ElementDeclaration resource, and a
    successful construction-stage result is recorded for downstream stages.
    """
    if not constraint_id.strip():
        raise ValueError("constraint_id is required")

    constraint, data_point_name = _require_normalized_constraint(
        normalized_graph,
        constraint_id,
    )
    schema_resource = _resolve_logical_schema_resource(
        logical_schema_graph,
        data_point_name,
    )

    _copy_graph(normalized_graph, output_graph)

    output_graph.add(
        (
            constraint,
            CONSTRAINT_VOCAB.boundLogicalSchemaResource,
            schema_resource,
        )
    )

    stage_result = exchange_successful_construction_stage_result(
        exchange_graph=output_graph,
        constraint_id=str(constraint),
        construction_stage="logical-schema-binding",
    )
    output_graph.add(
        (
            stage_result.result_id,
            UADEX.stageKnowledge,
            constraint,
        )
    )

    return stage_result


__all__ = [
    "bind_normalized_constraint_to_logical_schema",
]