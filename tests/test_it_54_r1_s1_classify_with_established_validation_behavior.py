"""IT-54R1S1: classify governed RDF with one established behavior."""

from __future__ import annotations

from importlib import import_module
from uuid import uuid4

import pytest
from rdflib import Graph, Literal, Namespace, RDF, URIRef
from rdflib.collection import Collection
from rdflib.namespace import PROV

from app.services.construction_exchange import (
    UADEX,
    read_construction_stage_result,
)


CV = Namespace("https://dynamicontology.com/uad36/constraint-vocabulary#")


def _round_trip(graph: Graph) -> Graph:
    return Graph().parse(data=graph.serialize(format="turtle"), format="turtle")


@pytest.mark.parametrize(
    "requirement,violation",
    [
        (
            "A value must be supplied in the applicable context.",
            "The value is absent in the applicable context.",
        ),
        (
            "At most one value may occur in the applicable context.",
            "More than one value occurs in the applicable context.",
        ),
    ],
    ids=["required-value", "maximum-one-occurrence"],
)
def test_it_54_r1_s1_classifies_with_one_established_validation_behavior(
    requirement: str,
    violation: str,
) -> None:
    # These are controlled governed-RDF fixtures, not selected workbook IDs.
    namespace = Namespace(f"urn:uad36:test:it54r1s1:{uuid4().hex}:")
    constraint = namespace.constraint
    source = namespace.source
    context = namespace.context
    schema_resource = namespace.data_point
    behavior = namespace.established_behavior
    other_behavior = namespace.other_behavior

    context_graph = Graph()
    for triple in (
        (constraint, RDF.type, CV.NormalizedConstraint),
        (constraint, CV.requirementText, Literal(requirement)),
        (constraint, CV.violationCondition, Literal(violation)),
        (constraint, CV.boundLogicalSchemaResource, schema_resource),
        (constraint, CV.applicableContext, context),
        (constraint, PROV.wasDerivedFrom, source),
        (context, RDF.type, CV.ConstraintContext),
        (context, PROV.wasDerivedFrom, source),
        (context, CV.schemaPath, namespace.path),
    ):
        context_graph.add(triple)
    Collection(context_graph, namespace.path, [namespace.parent, schema_resource])

    # The registry supplies established identities and governed matching facts.
    # The other definition shares the requirement but has a different violation.
    # Put it first: choosing the first behavior is not valid classification.
    behavior_graph = Graph()
    for triple in (
        (other_behavior, RDF.type, CV.ValidationBehavior),
        (other_behavior, CV.requirementText, Literal(requirement)),
        (
            other_behavior,
            CV.violationCondition,
            Literal("A different governed violation condition."),
        ),
        (behavior, RDF.type, CV.ValidationBehavior),
        (behavior, CV.requirementText, Literal(requirement)),
        (behavior, CV.violationCondition, Literal(violation)),
    ):
        behavior_graph.add(triple)

    context_graph = _round_trip(context_graph)
    behavior_graph = _round_trip(behavior_graph)
    context_before = set(context_graph)
    behaviors_before = set(behavior_graph)

    module = import_module("app.services.constraint_behavior_classification")
    classify = getattr(module, "classify_governed_constraint_behavior", None)
    assert callable(classify), (
        "IT-54R1S1 requires classify_governed_constraint_behavior("
        "context_graph=..., established_behaviors_graph=..., "
        "constraint_id=..., output_graph=...) to produce a governed RDF "
        "classification through the construction exchange contract. "
        "The dictionary classifier alone does not provide this operation."
    )

    output_graph = Graph()
    result = classify(
        context_graph=context_graph,
        established_behaviors_graph=behavior_graph,
        constraint_id=str(constraint),
        output_graph=output_graph,
    )

    assert set(context_graph) == context_before
    assert set(behavior_graph) == behaviors_before
    assert context_before.issubset(set(output_graph)), (
        "The classification must preserve upstream governed knowledge."
    )

    downstream = _round_trip(output_graph)
    classifications = set(downstream.objects(constraint, CV.behaviorClassification))
    assert len(classifications) == 1
    classification = next(iter(classifications))
    assert isinstance(classification, URIRef)
    assert (classification, RDF.type, CV.ValidationBehaviorClassification) in downstream
    assert set(downstream.objects(classification, CV.validationBehavior)) == {behavior}, (
        "Reuse the exact established behavior IRI determined by both governed facts."
    )
    assert set(downstream.objects(classification, CV.requirementText)) == {
        Literal(requirement)
    }
    assert set(downstream.objects(classification, CV.violationCondition)) == {
        Literal(violation)
    }
    assert set(downstream.objects(classification, CV.applicableContext)) == {context}
    assert (classification, PROV.wasDerivedFrom, source) in downstream

    record = read_construction_stage_result(
        exchange_graph=downstream,
        result_id=str(result.result_id),
    )
    assert record.constraint_id == str(constraint)
    assert record.construction_stage == "validation-behavior"
    assert record.construction_status == "GREEN"
    assert record.available_for_downstream is True
    assert (result.result_id, UADEX.stageKnowledge, classification) in downstream
