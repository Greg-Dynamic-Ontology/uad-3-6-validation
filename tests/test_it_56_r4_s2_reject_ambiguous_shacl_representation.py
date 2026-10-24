"""IT-56R4S2: preserve incompatible SHACL alternatives for review."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from rdflib import Graph, Literal, Namespace, RDF, URIRef
from rdflib.collection import Collection
from rdflib.namespace import PROV, SH

from app.services.construction_exchange import UADEX, read_construction_stage_result
from app.services.shacl_generation_agent import generate_governed_constraint_shacl


CV = Namespace("https://dynamicontology.com/uad36/constraint-vocabulary#")


@pytest.mark.parametrize("ambiguity", ["patterns", "templates"])
@pytest.mark.parametrize("reverse_order", [False, True], ids=["forward", "reverse"])
def test_it_56_r4_s2_rejects_ambiguous_shacl_representation(
    ambiguity: str,
    reverse_order: bool,
    tmp_path: Path,
) -> None:
    ns = Namespace(f"urn:uad36:test:it56r4s2:{uuid4().hex}:")
    constraint = ns.constraint
    bound = Graph()
    for triple in (
        (constraint, RDF.type, CV.NormalizedConstraint),
        (constraint, CV.requirementText, Literal("Apply the source-defined requirement.")),
        (constraint, CV.violationCondition, Literal("The source-defined condition is violated.")),
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

    first_pattern = ns.first_pattern
    second_pattern = ns.second_pattern if ambiguity == "patterns" else first_pattern
    alternatives = [
        (first_pattern, ns.first_template, SH.minCount, Literal(1)),
        (second_pattern, ns.second_template, SH.maxCount, Literal(0)),
    ]
    patterns = Graph()
    for pattern, template, component, value in (
        reversed(alternatives) if reverse_order else alternatives
    ):
        patterns.add((ns.behavior, CV.shaclImplementationPattern, pattern))
        patterns.add((pattern, RDF.type, CV.ShaclImplementationPattern))
        patterns.add((pattern, CV.propertyShapeTemplate, template))
        patterns.add((template, RDF.type, SH.PropertyShape))
        patterns.add((template, component, value))
    # The alternatives demand opposite occurrence conditions. Neither may be
    # chosen by graph order, lexical ordering, or a plausible default.
    bound = Graph().parse(data=bound.serialize(format="turtle"), format="turtle")
    patterns = Graph().parse(data=patterns.serialize(format="turtle"), format="turtle")
    bound_before = set(bound)
    patterns_before = set(patterns)
    output_path = tmp_path / "governed-shapes" / "ambiguous.ttl"
    output = Graph()

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
            "IT-56R4S2 requires governed EXCEPTION RDF recording the "
            "incompatible implementation alternatives and requiring review, "
            "without an executable SHACL artifact. The generator raised an "
            f"uncontracted ValueError: {error}",
            pytrace=False,
        )

    assert set(bound) == bound_before
    assert set(patterns) == patterns_before
    assert bound_before.issubset(set(output))
    assert not output_path.exists()
    assert not list(tmp_path.rglob("*.ttl"))
    assert not list(output.objects(constraint, CV.shaclRepresentation))
    assert not list(output.subjects(RDF.type, SH.NodeShape))
    assert not list(output.subject_objects(SH.targetClass))
    assert not list(output.subject_objects(SH.path))
    assert not list(output.objects(result.result_id, UADEX.stageKnowledge))

    downstream = Graph().parse(data=output.serialize(format="turtle"), format="turtle")
    record = read_construction_stage_result(
        exchange_graph=downstream, result_id=str(result.result_id)
    )
    assert record.constraint_id == str(constraint)
    assert record.construction_stage == "shacl-representation"
    assert record.construction_status == "EXCEPTION"
    assert record.available_for_downstream is False
    assert record.requires_review is True
    assert record.exception_reason and record.exception_reason.strip()
    assert (result.result_id, UADEX.forConstraint, constraint) in downstream
    assert (result.result_id, CV.validationBehavior, ns.behavior) in downstream
    assert (result.result_id, PROV.wasDerivedFrom, ns.source) in downstream

    candidates = set(downstream.objects(result.result_id, CV.candidateShaclRepresentation))
    assert len(candidates) == 2
    recorded_alternatives = set()
    for candidate in candidates:
        assert isinstance(candidate, URIRef)
        assert (candidate, RDF.type, CV.CandidateShaclRepresentation) in downstream
        candidate_patterns = list(downstream.objects(candidate, CV.shaclImplementationPattern))
        candidate_templates = list(downstream.objects(candidate, CV.propertyShapeTemplate))
        assert len(candidate_patterns) == len(candidate_templates) == 1
        recorded_alternatives.add((candidate_patterns[0], candidate_templates[0]))
        assert (candidate, CV.instanceRdfBinding, ns.binding) in downstream
        assert (candidate, CV.applicableContext, ns.context) in downstream
        template = candidate_templates[0]
        assert set(downstream.predicate_objects(template)) == set(
            patterns.predicate_objects(template)
        ), "Review must retain the actual incompatible template knowledge."
    assert recorded_alternatives == {
        (pattern, template) for pattern, template, _, _ in alternatives
    }
