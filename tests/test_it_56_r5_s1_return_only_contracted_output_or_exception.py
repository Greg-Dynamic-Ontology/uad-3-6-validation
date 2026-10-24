"""IT-56R5S1: SHACL generation is a bounded construction worker."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from rdflib import Graph, Literal, Namespace, RDF
from rdflib.collection import Collection
from rdflib.namespace import PROV, SH

from app.services.construction_exchange import (
    UADEX,
    ConstructionStageResultRecord,
    read_construction_stage_result,
)
from app.services.shacl_generation_agent import generate_governed_constraint_shacl


CV = Namespace("https://dynamicontology.com/uad36/constraint-vocabulary#")


def _round_trip(graph: Graph) -> Graph:
    return Graph().parse(data=graph.serialize(format="turtle"), format="turtle")


def _assert_no_findings(graph: Graph) -> None:
    assert not list(graph.subjects(RDF.type, SH.ValidationResult))
    assert not list(graph.subjects(RDF.type, SH.ValidationReport))
    for predicate in (
        SH.focusNode, SH.resultPath, SH.resultMessage, SH.resultSeverity,
        SH.sourceShape, SH.result, SH.conforms,
    ):
        assert not list(graph.subject_objects(predicate)), (
            f"SHACL generation produced runtime validation knowledge: {predicate}"
        )


@pytest.mark.parametrize(
    "pattern_count,expected_status",
    [(1, "GREEN"), (0, "EXCEPTION"), (2, "EXCEPTION")],
    ids=["generated", "unsupported", "ambiguous"],
)
def test_it_56_r5_s1_returns_only_contracted_output_or_exception(
    pattern_count: int,
    expected_status: str,
    tmp_path: Path,
) -> None:
    ns = Namespace(f"urn:uad36:test:it56r5s1:{uuid4().hex}:")
    constraint = ns.constraint
    requirement = Literal("Supply the governed value in its applicable context.")
    violation = Literal("The governed value is absent in its applicable context.")
    bound = Graph()
    for triple in (
        (constraint, RDF.type, CV.NormalizedConstraint),
        (constraint, CV.requirementText, requirement),
        (constraint, CV.violationCondition, violation),
        (constraint, CV.boundLogicalSchemaResource, ns.value_qname),
        (constraint, CV.applicableContext, ns.context),
        (constraint, CV.behaviorClassification, ns.classification),
        (constraint, CV.instanceRdfBinding, ns.binding),
        (constraint, PROV.wasDerivedFrom, ns.source),
        (ns.context, RDF.type, CV.ConstraintContext),
        (ns.context, CV.schemaPath, ns.schema_path),
        (ns.classification, RDF.type, CV.ValidationBehaviorClassification),
        (ns.classification, CV.validationBehavior, ns.behavior),
        (ns.classification, CV.applicableContext, ns.context),
        (ns.classification, CV.requirementText, requirement),
        (ns.classification, CV.violationCondition, violation),
        (ns.behavior, RDF.type, CV.ValidationBehavior),
        (ns.behavior, CV.requirementText, requirement),
        (ns.behavior, CV.violationCondition, violation),
        (ns.binding, RDF.type, CV.InstanceRdfBinding),
        (ns.binding, CV.boundLogicalSchemaResource, ns.value_qname),
        (ns.binding, CV.applicableContext, ns.context),
        (ns.binding, CV.behaviorClassification, ns.classification),
        (ns.binding, CV.validationBehavior, ns.behavior),
        (ns.binding, CV.focusClass, ns.focus_class),
        (ns.binding, CV.valuePredicate, ns.value_predicate),
        (ns.binding, CV.predicatePath, ns.predicate_path),
    ):
        bound.add(triple)
    schema_path = [ns.root_qname, ns.value_qname]
    Collection(bound, ns.schema_path, schema_path)
    Collection(bound, ns.predicate_path, [ns.value_predicate])

    patterns = Graph()
    for index in range(pattern_count):
        pattern = ns[f"pattern-{index}"]
        template = ns[f"template-{index}"]
        patterns.add((ns.behavior, CV.shaclImplementationPattern, pattern))
        patterns.add((pattern, RDF.type, CV.ShaclImplementationPattern))
        patterns.add((pattern, CV.propertyShapeTemplate, template))
        patterns.add((template, RDF.type, SH.PropertyShape))
        patterns.add((template, SH.minCount, Literal(index + 1)))
    bound = _round_trip(bound)
    patterns = _round_trip(patterns)
    bound_before = set(bound)
    patterns_before = set(patterns)
    output = Graph()
    artifact = tmp_path / "governed-shapes" / "constraint.ttl"

    result = generate_governed_constraint_shacl(
        bound_graph=bound,
        implementation_patterns_graph=patterns,
        constraint_id=str(constraint),
        output_path=artifact,
        output_graph=output,
    )
    assert isinstance(result, ConstructionStageResultRecord)
    assert set(bound) == bound_before
    assert set(patterns) == patterns_before
    assert bound_before.issubset(set(output))
    downstream = _round_trip(output)
    assert read_construction_stage_result(
        exchange_graph=downstream, result_id=str(result.result_id)
    ) == result
    assert result.constraint_id == str(constraint)
    assert result.construction_stage == "shacl-representation"
    assert result.construction_status == expected_status

    for resource in (constraint, ns.context, ns.classification, ns.behavior, ns.binding):
        assert {
            (predicate, value)
            for predicate, value in downstream.predicate_objects(resource)
            if not (resource == constraint and predicate == CV.shaclRepresentation)
        } == set(bound.predicate_objects(resource)), (
            f"Generation changed authoritative governed knowledge for {resource}."
        )
    assert list(Collection(downstream, ns.schema_path)) == schema_path
    assert list(Collection(downstream, ns.predicate_path)) == [ns.value_predicate]

    representations = set(downstream.objects(constraint, CV.shaclRepresentation))
    stage_knowledge = set(downstream.objects(result.result_id, UADEX.stageKnowledge))
    if expected_status == "GREEN":
        assert len(representations) == 1
        shape = next(iter(representations))
        assert (shape, RDF.type, SH.NodeShape) in downstream
        assert stage_knowledge == {shape}
        assert result.available_for_downstream is True
        assert result.requires_review is False
        assert result.exception_reason is None
        assert artifact.is_file()
        saved_shapes = Graph().parse(artifact, format="turtle")
        assert (shape, CV.implementsConstraint, constraint) in saved_shapes
        _assert_no_findings(saved_shapes)
    else:
        assert not representations
        assert not stage_knowledge
        assert not list(downstream.subjects(RDF.type, SH.NodeShape))
        assert not artifact.exists()
        assert not list(tmp_path.rglob("*.ttl"))
        assert result.available_for_downstream is False
        assert result.requires_review is True
        assert result.exception_reason

    _assert_no_findings(downstream)
    for _, predicate, value in set(output) - bound_before - patterns_before:
        if predicate == RDF.type:
            assert value in {
                SH.NodeShape, SH.PropertyShape, CV.CandidateShaclRepresentation,
                UADEX.ConstructionStageResult,
            }, "The worker generated an artifact outside SHACL construction."
