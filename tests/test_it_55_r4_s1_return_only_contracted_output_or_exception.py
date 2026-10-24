"""IT-55R4S1: Instance RDF binding is a bounded construction worker."""

from __future__ import annotations

from uuid import uuid4

import pytest
from rdflib import Graph, Literal, Namespace, RDF, RDFS
from rdflib.collection import Collection
from rdflib.namespace import OWL, PROV, SH, XSD

from app.services.construction_exchange import (
    UADEX,
    ConstructionStageResultRecord,
    read_construction_stage_result,
)
from app.services.instance_rdf_binding_agent import bind_governed_constraint_to_instance_rdf
from app.services.rdf_projection import UAD_SCHEMA


CV = Namespace("https://dynamicontology.com/uad36/constraint-vocabulary#")
LSM = Namespace("https://dynamicontology.com/uad36/logical-schema#")


def _round_trip(graph: Graph) -> Graph:
    return Graph().parse(data=graph.serialize(format="turtle"), format="turtle")


@pytest.mark.parametrize(
    "mapping_count,expected_status",
    [(1, "GREEN"), (0, "EXCEPTION"), (2, "EXCEPTION")],
    ids=["resolved", "unresolved", "ambiguous"],
)
def test_it_55_r4_s1_returns_only_contracted_output_or_exception(
    mapping_count: int,
    expected_status: str,
) -> None:
    ns = Namespace(f"urn:uad36:test:it55r4s1:{uuid4().hex}:")
    constraint = ns.constraint
    schema_path = [ns.root_qname, ns.value_qname]
    xml_namespace = "urn:uad36:test:bounded-instance-binding:xml"
    requirement = Literal("Supply the governed value in its applicable context.")
    violation = Literal("The governed value is absent in its applicable context.")

    classified = Graph()
    for triple in (
        (constraint, RDF.type, CV.NormalizedConstraint),
        (constraint, CV.requirementText, requirement),
        (constraint, CV.violationCondition, violation),
        (constraint, CV.boundLogicalSchemaResource, ns.value_qname),
        (constraint, CV.applicableContext, ns.context),
        (constraint, CV.behaviorClassification, ns.classification),
        (constraint, PROV.wasDerivedFrom, ns.source),
        (ns.context, RDF.type, CV.ConstraintContext),
        (ns.context, CV.schemaPath, ns.schema_path),
        (ns.classification, RDF.type, CV.ValidationBehaviorClassification),
        (ns.classification, CV.applicableContext, ns.context),
        (ns.classification, CV.validationBehavior, ns.behavior),
        (ns.classification, CV.requirementText, requirement),
        (ns.classification, CV.violationCondition, violation),
        (ns.behavior, RDF.type, CV.ValidationBehavior),
    ):
        classified.add(triple)
    Collection(classified, ns.schema_path, schema_path)

    model = Graph()
    for qname, local_name in zip(schema_path, ["PROPERTY", "AddressLineText"]):
        model.add((qname, RDF.type, LSM.QName))
        model.add((qname, LSM.namespace, Literal(xml_namespace)))
        model.add((qname, LSM.local_name, Literal(local_name)))
        model.add((qname, UAD_SCHEMA.sourceQName, Literal(f"{{{xml_namespace}}}{local_name}")))
    model.add((ns.root_qname, UAD_SCHEMA.projectsTo, ns.root_predicate))
    model.add((ns.root_predicate, RDF.type, OWL.ObjectProperty))
    model.add((ns.root_predicate, RDFS.range, ns.root_class))
    model.add((ns.root_class, RDF.type, OWL.Class))
    value_predicates = {ns[f"value-predicate-{index}"] for index in range(mapping_count)}
    for predicate in value_predicates:
        model.add((ns.value_qname, UAD_SCHEMA.projectsTo, predicate))
        model.add((predicate, RDF.type, OWL.DatatypeProperty))
        model.add((predicate, RDFS.range, XSD.string))

    classified = _round_trip(classified)
    model = _round_trip(model)
    classified_before = set(classified)
    model_before = set(model)
    output = Graph()
    result = bind_governed_constraint_to_instance_rdf(
        classified_graph=classified,
        projection_model_graph=model,
        constraint_id=str(constraint),
        output_graph=output,
    )
    assert isinstance(result, ConstructionStageResultRecord)
    assert set(classified) == classified_before
    assert set(model) == model_before
    assert classified_before.issubset(set(output))
    downstream = _round_trip(output)
    assert read_construction_stage_result(
        exchange_graph=downstream, result_id=str(result.result_id)
    ) == result
    assert result.constraint_id == str(constraint)
    assert result.construction_stage == "instance-rdf-binding"
    assert result.construction_status == expected_status

    # The only new statement on the normalized constraint may be its binding.
    assert {
        (predicate, value)
        for predicate, value in downstream.predicate_objects(constraint)
        if predicate != CV.instanceRdfBinding
    } == set(classified.predicate_objects(constraint))
    for resource in (ns.context, ns.classification, ns.behavior):
        assert set(downstream.predicate_objects(resource)) == set(
            classified.predicate_objects(resource)
        )
    assert list(Collection(downstream, ns.schema_path)) == schema_path

    bindings = set(downstream.objects(constraint, CV.instanceRdfBinding))
    stage_knowledge = set(downstream.objects(result.result_id, UADEX.stageKnowledge))
    if expected_status == "GREEN":
        assert len(bindings) == 1
        binding = next(iter(bindings))
        assert (binding, RDF.type, CV.InstanceRdfBinding) in downstream
        assert stage_knowledge == {binding}
        assert result.available_for_downstream is True
        assert result.requires_review is False
        assert result.exception_reason is None
        assert set(downstream.objects(binding, CV.valuePredicate)) == value_predicates
    else:
        assert not bindings
        assert not stage_knowledge
        assert not list(downstream.subjects(RDF.type, CV.InstanceRdfBinding))
        assert result.available_for_downstream is False
        assert result.requires_review is True
        assert result.exception_reason

    # Newly generated types are limited to binding knowledge and exchange
    # metadata. Inherited ontology classes are not worker-generated output.
    added = set(output) - classified_before - model_before
    for _, predicate, object_value in added:
        assert not str(predicate).startswith(str(SH)), "The worker generated SHACL."
        if predicate == RDF.type:
            assert object_value in {
                CV.InstanceRdfBinding,
                CV.CandidateInstanceRdfBinding,
                UADEX.ConstructionStageResult,
            }, "The worker generated another stage's artifact or report finding."
        assert predicate != UAD_SCHEMA.projectsTo, "The worker redesigned the projector."
    assert not list(downstream.subjects(RDF.type, SH.ValidationResult))
    assert not list(downstream.subjects(RDF.type, SH.ValidationReport))
    assert set(downstream.subjects(RDF.type, CV.NormalizedConstraint)) == {constraint}
    assert set(downstream.subjects(RDF.type, CV.ConstraintContext)) == {ns.context}
    assert set(downstream.subjects(RDF.type, CV.ValidationBehaviorClassification)) == {
        ns.classification
    }
