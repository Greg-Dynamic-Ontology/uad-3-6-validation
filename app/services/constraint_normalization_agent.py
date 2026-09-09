"""Normalize governed source constraints into stable RDF knowledge."""

from __future__ import annotations

from dataclasses import dataclass

from rdflib import Literal, Namespace, RDF, URIRef


UADCON = Namespace("https://dynamicontology.com/uad36/constraint/")
UADCV = Namespace("https://dynamicontology.com/uad36/constraint-vocabulary#")


@dataclass(frozen=True)
class NormalizedConstraintResult:
    """Identity summary for one normalized governed constraint."""

    constraint_id: str
    unique_id: str
    data_point_name: str
    source_rule_id: str


def normalize_governed_constraint(
    *,
    governed_source: dict,
    output_graph,
) -> NormalizedConstraintResult:
    """Produce normalized constraint RDF from sufficient governed source knowledge."""
    required_fields = (
        "unique_id",
        "data_point_name",
        "source_rule_id",
        "requirement_text",
        "violation_condition",
        "severity",
        "context_fields",
        "source_locator",
    )
    missing_fields = [
        field
        for field in required_fields
        if field not in governed_source
    ]
    if missing_fields:
        raise ValueError(
            "Insufficient governed source knowledge; missing: "
            + ", ".join(missing_fields)
        )

    unique_id = str(governed_source["unique_id"])
    constraint = URIRef(f"{UADCON}{unique_id}")

    output_graph.add((constraint, RDF.type, UADCV.NormalizedConstraint))
    output_graph.add(
        (constraint, UADCV.governedUniqueId, Literal(unique_id))
    )
    output_graph.add(
        (
            constraint,
            UADCV.dataPointName,
            Literal(governed_source["data_point_name"]),
        )
    )
    output_graph.add(
        (
            constraint,
            UADCV.sourceRuleId,
            Literal(governed_source["source_rule_id"]),
        )
    )
    output_graph.add(
        (
            constraint,
            UADCV.requirementText,
            Literal(governed_source["requirement_text"]),
        )
    )
    output_graph.add(
        (
            constraint,
            UADCV.violationCondition,
            Literal(governed_source["violation_condition"]),
        )
    )
    output_graph.add(
        (
            constraint,
            UADCV.severity,
            Literal(governed_source["severity"]),
        )
    )
    output_graph.add(
        (
            constraint,
            UADCV.sourceLocator,
            Literal(governed_source["source_locator"]),
        )
    )

    for index, context_value in enumerate(
        governed_source["context_fields"],
        start=1,
    ):
        context_node = URIRef(f"{constraint}/source-context/{index}")
        output_graph.add(
            (constraint, UADCV.hasSourceContext, context_node)
        )
        output_graph.add(
            (context_node, UADCV.contextOrder, Literal(index))
        )
        output_graph.add(
            (
                context_node,
                UADCV.contextValue,
                Literal(context_value),
            )
        )

    return NormalizedConstraintResult(
        constraint_id=str(constraint),
        unique_id=unique_id,
        data_point_name=str(governed_source["data_point_name"]),
        source_rule_id=str(governed_source["source_rule_id"]),
    )


__all__ = [
    "NormalizedConstraintResult",
    "normalize_governed_constraint",
]
