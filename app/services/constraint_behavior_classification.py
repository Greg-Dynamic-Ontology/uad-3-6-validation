"""Classify governed constraint behavior without forcing unknown patterns."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Mapping

from rdflib import Graph, Literal, Namespace, RDF, URIRef
from rdflib.namespace import PROV

from app.services.construction_exchange import (
    UADEX,
    ConstructionStageResultRecord,
    exchange_successful_construction_stage_result,
    exchange_construction_stage_exception,
)


CV = Namespace("https://dynamicontology.com/uad36/constraint-vocabulary#")


@dataclass(frozen=True)
class ConstraintBehaviorClassification:
    """Classification result for one governed constraint."""

    constraint_id: str
    matched_behavior_id: str | None
    is_previously_unknown: bool
    proposed_behavior_id: str | None
    requires_governance: bool
    eligible_for_repeated_implementation: bool


def classify_constraint_behavior(
    *,
    constraint: Mapping[str, object],
    established_behaviors: Mapping[str, Mapping[str, object]],
) -> ConstraintBehaviorClassification:
    """
    Classify one governed constraint against established behavior patterns.

    If no established behavior matches the governed violation kind, identify
    a new candidate behavior and stop it for governance rather than forcing
    it into an existing pattern.
    """
    constraint_id = str(constraint["constraint_id"])
    violation_kind = str(constraint.get("violation_kind", ""))

    for behavior_id, behavior in established_behaviors.items():
        if str(behavior.get("violation_kind", "")) == violation_kind:
            return ConstraintBehaviorClassification(
                constraint_id=constraint_id,
                matched_behavior_id=behavior_id,
                is_previously_unknown=False,
                proposed_behavior_id=None,
                requires_governance=False,
                eligible_for_repeated_implementation=True,
            )

    proposed_behavior_id = None
    if violation_kind == "ComparisonFailure":
        proposed_behavior_id = "Comparison"

    return ConstraintBehaviorClassification(
        constraint_id=constraint_id,
        matched_behavior_id=None,
        is_previously_unknown=True,
        proposed_behavior_id=proposed_behavior_id,
        requires_governance=True,
        eligible_for_repeated_implementation=False,
    )


def _one_value(graph: Graph, subject: URIRef, predicate: URIRef):
    values = set(graph.objects(subject, predicate))
    if len(values) != 1:
        raise ValueError(f"{subject} must have exactly one {predicate} value.")
    return next(iter(values))


def classify_governed_constraint_behavior(
    *,
    context_graph: Graph,
    established_behaviors_graph: Graph,
    constraint_id: str,
    output_graph: Graph,
) -> ConstructionStageResultRecord:
    """Reuse an established RDF behavior with an exact governed fact match.

    This operation matches the requirement and violation together. It does not
    infer equivalence between differently worded requirements or generate an
    executable representation.
    """
    if output_graph is context_graph or output_graph is established_behaviors_graph:
        raise ValueError("output_graph must be separate from the input graphs.")
    if not constraint_id.strip():
        raise ValueError("constraint_id is required.")

    constraint = URIRef(constraint_id)
    if (constraint, RDF.type, CV.NormalizedConstraint) not in context_graph:
        raise ValueError("constraint_id must identify a NormalizedConstraint.")

    requirement = _one_value(context_graph, constraint, CV.requirementText)
    violation = _one_value(context_graph, constraint, CV.violationCondition)
    for name, value in (("requirement", requirement), ("violation", violation)):
        if not isinstance(value, Literal) or not str(value).strip():
            raise ValueError(f"The governed {name} must be a nonblank RDF literal.")

    context = _one_value(context_graph, constraint, CV.applicableContext)
    binding = _one_value(context_graph, constraint, CV.boundLogicalSchemaResource)
    if not isinstance(context, URIRef) or not isinstance(binding, URIRef):
        raise ValueError("The applicable context and schema binding must be IRIs.")
    if (context, RDF.type, CV.ConstraintContext) not in context_graph:
        raise ValueError("The applicable context must identify a ConstraintContext.")

    sources = set(context_graph.objects(constraint, PROV.wasDerivedFrom))
    if not sources:
        raise ValueError("The constraint must preserve governed source provenance.")

    matches = {
        behavior
        for behavior in established_behaviors_graph.subjects(
            RDF.type, CV.ValidationBehavior
        )
        if isinstance(behavior, URIRef)
        and set(established_behaviors_graph.objects(behavior, CV.requirementText))
        == {requirement}
        and set(established_behaviors_graph.objects(behavior, CV.violationCondition))
        == {violation}
    }
    if not matches:
        # Unknown behavior is governed construction knowledge, not a runtime
        # appraisal finding and not permission to invent a behavior identity.
        for graph in (context_graph, established_behaviors_graph):
            for prefix, namespace in graph.namespaces():
                output_graph.bind(prefix, namespace, replace=False)
            for triple in graph:
                output_graph.add(triple)

        result = exchange_construction_stage_exception(
            exchange_graph=output_graph,
            constraint_id=str(constraint),
            construction_stage="validation-behavior",
            exception_reason=(
                "No established validation behavior matches the governed "
                "requirement and violation condition. A new behavior "
                "classification may be required; governance review is required."
            ),
            requires_review=True,
        )
        for triple in (
            (result.result_id, CV.requirementText, requirement),
            (result.result_id, CV.violationCondition, violation),
            (result.result_id, CV.applicableContext, context),
            (result.result_id, CV.newBehaviorClassificationRequired, Literal(True)),
        ):
            output_graph.add(triple)
        for source in sources:
            output_graph.add((result.result_id, PROV.wasDerivedFrom, source))
        return result

    if len(matches) > 1:
        # Preserve every candidate; graph iteration order is not authority.
        for graph in (context_graph, established_behaviors_graph):
            for prefix, namespace in graph.namespaces():
                output_graph.bind(prefix, namespace, replace=False)
            for triple in graph:
                output_graph.add(triple)

        result = exchange_construction_stage_exception(
            exchange_graph=output_graph,
            constraint_id=str(constraint),
            construction_stage="validation-behavior",
            exception_reason=(
                "The governed requirement and violation condition match "
                f"{len(matches)} established validation behaviors. "
                "The classification is ambiguous; review is required. "
                "No candidate behavior has been selected."
            ),
            requires_review=True,
        )
        for triple in (
            (result.result_id, CV.requirementText, requirement),
            (result.result_id, CV.violationCondition, violation),
            (result.result_id, CV.applicableContext, context),
        ):
            output_graph.add(triple)
        for candidate in sorted(matches, key=str):
            output_graph.add((result.result_id, CV.candidateBehavior, candidate))
        for source in sources:
            output_graph.add((result.result_id, PROV.wasDerivedFrom, source))
        return result
    behavior = next(iter(matches))

    # Keep the established behavior IRI; mint only the classification identity.
    digest = sha256(str(behavior).encode("utf-8")).hexdigest()
    classification = URIRef(f"{constraint}/behavior-classification/{digest}")

    for graph in (context_graph, established_behaviors_graph):
        for prefix, namespace in graph.namespaces():
            output_graph.bind(prefix, namespace, replace=False)
        for triple in graph:
            output_graph.add(triple)

    for triple in (
        (constraint, CV.behaviorClassification, classification),
        (classification, RDF.type, CV.ValidationBehaviorClassification),
        (classification, CV.validationBehavior, behavior),
        (classification, CV.requirementText, requirement),
        (classification, CV.violationCondition, violation),
        (classification, CV.applicableContext, context),
        (classification, PROV.wasDerivedFrom, behavior),
    ):
        output_graph.add(triple)
    for source in sources:
        output_graph.add((classification, PROV.wasDerivedFrom, source))

    result = exchange_successful_construction_stage_result(
        exchange_graph=output_graph,
        constraint_id=str(constraint),
        construction_stage="validation-behavior",
    )
    output_graph.add((result.result_id, UADEX.stageKnowledge, classification))
    return result

__all__ = [
    "ConstraintBehaviorClassification",
    "classify_constraint_behavior",
    "classify_governed_constraint_behavior",
]
