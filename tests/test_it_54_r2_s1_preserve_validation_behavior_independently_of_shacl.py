"""IT-54R2S1: governed behavior remains independent of SHACL."""

from __future__ import annotations

from uuid import uuid4

from rdflib import Graph, Literal, Namespace, RDF, URIRef
from rdflib.namespace import PROV, SH

from app.services.constraint_behavior_classification import (
    classify_governed_constraint_behavior,
)
from app.services.construction_exchange import read_construction_stage_result


CV = Namespace("https://dynamicontology.com/uad36/constraint-vocabulary#")


def _round_trip(graph: Graph) -> Graph:
    return Graph().parse(data=graph.serialize(format="turtle"), format="turtle")


def test_it_54_r2_s1_preserves_validation_behavior_independently_of_shacl() -> None:
    ns = Namespace(f"urn:uad36:test:it54r2s1:{uuid4().hex}:")
    constraint = ns.constraint
    behavior = ns.behavior
    context = ns.context
    source = ns.source
    requirement = Literal("Supply a nonblank value in the applicable context.")
    violation = Literal("The applicable value is absent or blank.")

    context_graph = Graph()
    for triple in (
        (constraint, RDF.type, CV.NormalizedConstraint),
        (constraint, CV.requirementText, requirement),
        (constraint, CV.violationCondition, violation),
        (constraint, CV.boundLogicalSchemaResource, ns.schema_resource),
        (constraint, CV.applicableContext, context),
        (constraint, PROV.wasDerivedFrom, source),
        (context, RDF.type, CV.ConstraintContext),
    ):
        context_graph.add(triple)
    context_graph = _round_trip(context_graph)
    input_before = set(context_graph)

    registry = Graph()
    for triple in (
        (behavior, RDF.type, CV.ValidationBehavior),
        (behavior, CV.requirementText, requirement),
        (behavior, CV.violationCondition, violation),
    ):
        registry.add(triple)

    # First classify with no executable representation or SHACL knowledge.
    first_output = Graph()
    first_result = classify_governed_constraint_behavior(
        context_graph=context_graph,
        established_behaviors_graph=_round_trip(registry),
        constraint_id=str(constraint),
        output_graph=first_output,
    )
    first_output = _round_trip(first_output)
    classifications = set(first_output.objects(constraint, CV.behaviorClassification))
    assert len(classifications) == 1
    classification = next(iter(classifications))
    assert isinstance(classification, URIRef)

    expected_meaning = {
        (classification, RDF.type, CV.ValidationBehaviorClassification),
        (classification, CV.validationBehavior, behavior),
        (classification, CV.requirementText, requirement),
        (classification, CV.violationCondition, violation),
        (classification, CV.applicableContext, context),
        (classification, PROV.wasDerivedFrom, source),
    }
    assert expected_meaning.issubset(set(first_output))
    assert not any(str(predicate).startswith(str(SH)) for _, predicate, _ in first_output)

    # Add two alternative representation resources for the SAME behavior.
    # These are illustrative registry metadata, not generated executable code.
    for triple in (
        (ns.shacl_representation, CV.implementsBehavior, behavior),
        (ns.shacl_representation, RDF.type, SH.PropertyShape),
        (ns.shacl_representation, SH.path, ns.instance_property),
        (ns.shacl_representation, SH.minCount, Literal(1)),
        (ns.shacl_representation, SH.minLength, Literal(1)),
        (ns.other_representation, CV.implementsBehavior, behavior),
        (ns.other_representation, RDF.type, ns.AlternativeExecutableRepresentation),
    ):
        registry.add(triple)

    for minimum_count in (1, 9):
        # Even inconsistent implementation metadata cannot redefine governed
        # meaning. Checking executable correctness belongs to a later stage.
        registry.set((ns.shacl_representation, SH.minCount, Literal(minimum_count)))
        registry_input = _round_trip(registry)
        registry_before = set(registry_input)
        output = Graph()
        result = classify_governed_constraint_behavior(
            context_graph=context_graph,
            established_behaviors_graph=registry_input,
            constraint_id=str(constraint),
            output_graph=output,
        )
        downstream = _round_trip(output)

        assert set(context_graph) == input_before
        assert set(registry_input) == registry_before
        assert input_before.issubset(set(downstream))
        assert set(downstream.objects(constraint, CV.behaviorClassification)) == {
            classification
        }
        assert expected_meaning.issubset(set(downstream))
        assert set(downstream.objects(classification, CV.requirementText)) == {
            requirement
        }
        assert set(downstream.objects(classification, CV.violationCondition)) == {
            violation
        }
        assert set(downstream.subjects(CV.implementsBehavior, behavior)) == {
            ns.shacl_representation,
            ns.other_representation,
        }
        assert not any(
            str(predicate).startswith(str(SH))
            for predicate, _ in downstream.predicate_objects(classification)
        ), "SHACL predicates must not define the governed behavior classification."
        record = read_construction_stage_result(
            exchange_graph=downstream, result_id=str(result.result_id)
        )
        assert record.constraint_id == str(constraint)
        assert record.construction_status == "GREEN"
        assert record.available_for_downstream is True

    first_record = read_construction_stage_result(
        exchange_graph=first_output, result_id=str(first_result.result_id)
    )
    assert first_record.construction_status == "GREEN"
