"""IT-54R3S1: preserve unknown behavior as reviewable exception RDF."""

from __future__ import annotations

from uuid import uuid4

import pytest
from rdflib import Dataset, Graph, Literal, Namespace, RDF
from rdflib.namespace import PROV

from app.services.constraint_behavior_classification import (
    classify_governed_constraint_behavior,
)
from app.services.construction_exchange import (
    UADEX,
    read_construction_stage_result,
)


CV = Namespace("https://dynamicontology.com/uad36/constraint-vocabulary#")


@pytest.mark.parametrize(
    "registry_case",
    ["empty-registry", "requirement-only-match", "violation-only-match"],
)
def test_it_54_r3_s1_reports_unknown_validation_behavior(
    registry_case: str,
) -> None:
    ns = Namespace(f"urn:uad36:test:it54r3s1:{uuid4().hex}:")
    constraint = ns.constraint
    requirement = Literal("The governed value must satisfy the source requirement.")
    violation = Literal("The source-defined relationship between values is violated.")

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
    if registry_case != "empty-registry":
        registry.add((ns.established_behavior, RDF.type, CV.ValidationBehavior))
        registry.add((
            ns.established_behavior,
            CV.requirementText,
            requirement if registry_case == "requirement-only-match"
            else Literal("A different governed requirement."),
        ))
        registry.add((
            ns.established_behavior,
            CV.violationCondition,
            violation if registry_case == "violation-only-match"
            else Literal("A different governed violation condition."),
        ))

    context_graph = Graph().parse(
        data=context_graph.serialize(format="turtle"), format="turtle"
    )
    registry = Graph().parse(
        data=registry.serialize(format="turtle"), format="turtle"
    )
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
            "IT-54R3S1 requires governed EXCEPTION RDF for an unknown "
            "validation behavior, preserving source meaning and routing "
            f"the constraint for review. Got an uncontracted ValueError: {error}",
            pytrace=False,
        )

    assert set(context_graph) == input_before
    assert set(registry) == registry_before
    assert input_before.issubset(set(output))
    assert not list(output.objects(constraint, CV.behaviorClassification))
    assert not list(output.subjects(RDF.type, CV.ValidationBehaviorClassification))
    assert not list(output.objects(result.result_id, UADEX.stageKnowledge))

    record = read_construction_stage_result(
        exchange_graph=output, result_id=str(result.result_id)
    )
    assert record.constraint_id == str(constraint)
    assert record.construction_stage == "validation-behavior"
    assert record.construction_status == "EXCEPTION"
    assert record.available_for_downstream is False
    assert record.requires_review is True
    assert record.exception_reason and record.exception_reason.strip()
    assert (result.result_id, UADEX.forConstraint, constraint) in output
    assert (result.result_id, CV.requirementText, requirement) in output
    assert (result.result_id, CV.violationCondition, violation) in output
    assert (result.result_id, PROV.wasDerivedFrom, ns.source) in output
    assert (
        result.result_id,
        CV.newBehaviorClassificationRequired,
        Literal(True),
    ) in output, "The exception must identify the need to review a new classification."

    # Exception RDF must be usable in a named Batch Results Graph. Serialize
    # that graph's contents as Turtle without invoking deprecated TriG APIs.
    batch = Dataset().graph(ns.batch_results)
    for triple in output:
        batch.add(triple)
    restored = Graph().parse(data=batch.serialize(format="turtle"), format="turtle")
    assert read_construction_stage_result(
        exchange_graph=restored, result_id=str(result.result_id)
    ) == record
    assert (constraint, CV.requirementText, requirement) in restored
    assert (constraint, CV.violationCondition, violation) in restored
