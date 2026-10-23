"""IT-54R3S2: preserve incompatible behavior candidates for review."""

from __future__ import annotations

from uuid import uuid4

import pytest
from rdflib import Graph, Literal, Namespace, RDF
from rdflib.namespace import OWL, PROV

from app.services.constraint_behavior_classification import (
    classify_governed_constraint_behavior,
)
from app.services.construction_exchange import (
    UADEX,
    read_construction_stage_result,
)


CV = Namespace("https://dynamicontology.com/uad36/constraint-vocabulary#")


def _round_trip(graph: Graph) -> Graph:
    return Graph().parse(data=graph.serialize(format="turtle"), format="turtle")


@pytest.mark.parametrize("reverse_order", [False, True], ids=["forward", "reverse"])
def test_it_54_r3_s2_rejects_ambiguous_validation_behavior(
    reverse_order: bool,
) -> None:
    ns = Namespace(f"urn:uad36:test:it54r3s2:{uuid4().hex}:")
    constraint = ns.constraint
    requirement = Literal("The applicable value must satisfy the governed requirement.")
    violation = Literal("The source-defined applicable value requirement is violated.")
    candidates = (ns.first_behavior, ns.second_behavior)

    context_graph = Graph()
    for triple in (
        (constraint, RDF.type, CV.NormalizedConstraint),
        (constraint, CV.requirementText, requirement),
        (constraint, CV.violationCondition, violation),
        (constraint, CV.boundLogicalSchemaResource, ns.schema_resource),
        (constraint, CV.applicableContext, ns.context),
        (constraint, PROV.wasDerivedFrom, ns.source),
        (ns.context, RDF.type, CV.ConstraintContext),
    ):
        context_graph.add(triple)

    registry = Graph()
    for behavior in reversed(candidates) if reverse_order else candidates:
        registry.add((behavior, RDF.type, CV.ValidationBehavior))
        registry.add((behavior, CV.requirementText, requirement))
        registry.add((behavior, CV.violationCondition, violation))
    # Governed registry knowledge explicitly rules out treating these as aliases.
    registry.add((candidates[0], OWL.differentFrom, candidates[1]))

    context_graph = _round_trip(context_graph)
    registry = _round_trip(registry)
    input_before = set(context_graph)
    registry_before = set(registry)
    output = Graph()
    try:
        result = classify_governed_constraint_behavior(
            context_graph=context_graph,
            established_behaviors_graph=registry,
            constraint_id=str(constraint),
            output_graph=output,
        )
    except ValueError as error:
        pytest.fail(
            "IT-54R3S2 requires governed EXCEPTION RDF recording both "
            "candidate behaviors and routing the constraint for review. "
            f"The classifier raised an uncontracted ValueError: {error}",
            pytrace=False,
        )

    assert set(context_graph) == input_before
    assert set(registry) == registry_before
    assert input_before.issubset(set(output))
    assert not list(output.objects(constraint, CV.behaviorClassification))
    assert not list(output.subjects(RDF.type, CV.ValidationBehaviorClassification))
    assert not list(output.objects(result.result_id, UADEX.stageKnowledge))

    downstream = _round_trip(output)
    record = read_construction_stage_result(
        exchange_graph=downstream, result_id=str(result.result_id)
    )
    assert record.constraint_id == str(constraint)
    assert record.construction_stage == "validation-behavior"
    assert record.construction_status == "EXCEPTION"
    assert record.requires_review is True
    assert record.available_for_downstream is False
    assert record.exception_reason and record.exception_reason.strip()
    assert (result.result_id, UADEX.forConstraint, constraint) in downstream
    assert set(downstream.objects(result.result_id, CV.candidateBehavior)) == set(
        candidates
    ), "The exception must identify both exact candidate behavior IRIs."
    for behavior in candidates:
        assert (behavior, RDF.type, CV.ValidationBehavior) in downstream
        assert (behavior, CV.requirementText, requirement) in downstream
        assert (behavior, CV.violationCondition, violation) in downstream
    assert (candidates[0], OWL.differentFrom, candidates[1]) in downstream
    assert (result.result_id, CV.requirementText, requirement) in downstream
    assert (result.result_id, CV.violationCondition, violation) in downstream
    assert (result.result_id, CV.applicableContext, ns.context) in downstream
    assert (result.result_id, PROV.wasDerivedFrom, ns.source) in downstream
