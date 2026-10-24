"""IT-56R4S1: no executable SHACL without a governed implementation pattern."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from rdflib import Dataset, Graph, Literal, Namespace, RDF
from rdflib.collection import Collection
from rdflib.compare import isomorphic
from rdflib.namespace import PROV, SH

from app.services.construction_exchange import (
    UADEX,
    read_construction_stage_result,
)
from app.services.shacl_generation_agent import generate_governed_constraint_shacl


CV = Namespace("https://dynamicontology.com/uad36/constraint-vocabulary#")


@pytest.mark.parametrize(
    "registry_case", ["empty-registry", "unrelated-pattern-only"]
)
def test_it_56_r4_s1_rejects_behavior_without_governed_shacl_pattern(
    registry_case: str,
    tmp_path: Path,
) -> None:
    ns = Namespace(f"urn:uad36:test:it56r4s1:{uuid4().hex}:")
    constraint = ns.constraint
    requirement = Literal("Apply the governed requirement in its applicable context.")
    violation = Literal("The source-defined requirement is violated.")

    # A valid bounded-worker input fixture. Its meaning, context, behavior,
    # and Instance RDF binding are present; only its implementation is absent.
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
    Collection(bound, ns.schema_path, [ns.root_qname, ns.value_qname])
    Collection(bound, ns.predicate_path, [ns.value_predicate])

    patterns = Graph()
    if registry_case == "unrelated-pattern-only":
        patterns.add((ns.other_behavior, CV.shaclImplementationPattern, ns.other_pattern))
        patterns.add((ns.other_pattern, RDF.type, CV.ShaclImplementationPattern))
        patterns.add((ns.other_pattern, CV.propertyShapeTemplate, ns.other_template))
        patterns.add((ns.other_template, RDF.type, SH.PropertyShape))
        patterns.add((ns.other_template, SH.minCount, Literal(1)))
    bound = Graph().parse(data=bound.serialize(format="turtle"), format="turtle")
    patterns = Graph().parse(data=patterns.serialize(format="turtle"), format="turtle")
    bound_before = set(bound)
    patterns_before = set(patterns)
    output = Graph()
    output_path = tmp_path / "governed-shapes" / "unsupported.ttl"
    assert not output_path.exists()

    try:
        result = generate_governed_constraint_shacl(
            bound_graph=bound,
            implementation_patterns_graph=patterns,
            constraint_id=str(constraint),
            output_path=output_path,
            output_graph=output,
        )
    except ValueError as error:
        pytest.fail(
            "IT-56R4S1 requires governed EXCEPTION RDF identifying the "
            "unsupported validation behavior and routing the constraint "
            "for review, without generating a SHACL artifact. The generator "
            f"raised an uncontracted ValueError: {error}",
            pytrace=False,
        )

    assert set(bound) == bound_before
    assert set(patterns) == patterns_before
    assert bound_before.issubset(set(output))
    assert not output_path.exists(), "Unsupported behavior must not produce an artifact."
    assert not list(tmp_path.rglob("*.ttl")), "No alternative SHACL file may be invented."
    assert not list(output.objects(constraint, CV.shaclRepresentation))
    assert not list(output.subjects(RDF.type, SH.NodeShape))
    assert not list(output.objects(result.result_id, UADEX.stageKnowledge))

    recorded = read_construction_stage_result(
        exchange_graph=output, result_id=str(result.result_id)
    )
    assert recorded.constraint_id == str(constraint)
    assert recorded.construction_stage == "shacl-representation"
    assert recorded.construction_status == "EXCEPTION"
    assert recorded.available_for_downstream is False
    assert recorded.requires_review is True
    assert recorded.exception_reason and recorded.exception_reason.strip()
    assert (result.result_id, UADEX.forConstraint, constraint) in output
    assert (result.result_id, CV.validationBehavior, ns.behavior) in output
    assert (result.result_id, PROV.wasDerivedFrom, ns.source) in output
    added = set(output) - bound_before - patterns_before
    assert not any(str(predicate).startswith(str(SH)) for _, predicate, _ in added)
    assert not any(
        predicate in {CV.shaclImplementationPattern, CV.propertyShapeTemplate}
        or (predicate == RDF.type and value == CV.ShaclImplementationPattern)
        for _, predicate, value in added
    ), "The generator must not invent an implementation pattern."

    batch = Dataset().graph(ns.batch_results)
    for triple in output:
        batch.add(triple)
    restored = Graph().parse(data=batch.serialize(format="turtle"), format="turtle")
    assert isomorphic(batch, restored)
    assert read_construction_stage_result(
        exchange_graph=restored, result_id=str(result.result_id)
    ) == recorded
