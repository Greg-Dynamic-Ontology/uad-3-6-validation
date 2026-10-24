"""IT-55R3S1: unresolved projection knowledge produces exception RDF."""

from __future__ import annotations

from uuid import uuid4

import pytest
from rdflib import Dataset, Graph, Literal, Namespace, RDF, RDFS
from rdflib.collection import Collection
from rdflib.compare import isomorphic
from rdflib.namespace import OWL, PROV, XSD

from app.services.construction_exchange import (
    UADEX,
    read_construction_stage_result,
)
from app.services.instance_rdf_binding_agent import (
    bind_governed_constraint_to_instance_rdf,
)
from app.services.rdf_projection import UAD_SCHEMA


CV = Namespace("https://dynamicontology.com/uad36/constraint-vocabulary#")
LSM = Namespace("https://dynamicontology.com/uad36/logical-schema#")


@pytest.mark.parametrize(
    "missing_index", [1, 2], ids=["missing-context-predicate", "missing-value-predicate"]
)
def test_it_55_r3_s1_rejects_unresolved_instance_rdf_binding(
    missing_index: int,
) -> None:
    ns = Namespace(f"urn:uad36:test:it55r3s1:{uuid4().hex}:")
    constraint = ns.constraint
    schema_path = [ns.property_qname, ns.address_qname, ns.value_qname]
    missing_resource = schema_path[missing_index]
    xml_namespace = "urn:uad36:test:unresolved-binding:xml"

    classified = Graph()
    for triple in (
        (constraint, RDF.type, CV.NormalizedConstraint),
        (constraint, CV.requirementText, Literal("Supply the governed address line.")),
        (constraint, CV.violationCondition, Literal("The governed address line is absent.")),
        (constraint, CV.boundLogicalSchemaResource, schema_path[-1]),
        (constraint, CV.applicableContext, ns.context),
        (constraint, CV.behaviorClassification, ns.classification),
        (constraint, PROV.wasDerivedFrom, ns.source),
        (ns.context, RDF.type, CV.ConstraintContext),
        (ns.context, CV.schemaPath, ns.schema_path),
        (ns.classification, RDF.type, CV.ValidationBehaviorClassification),
        (ns.classification, CV.applicableContext, ns.context),
        (ns.classification, CV.validationBehavior, ns.behavior),
        (ns.behavior, RDF.type, CV.ValidationBehavior),
    ):
        classified.add(triple)
    Collection(classified, ns.schema_path, schema_path)

    model = Graph()
    mappings = [
        ("PROPERTY", ns.property_predicate, ns.property_class, OWL.ObjectProperty),
        ("ADDRESS", ns.address_predicate, ns.address_class, OWL.ObjectProperty),
        ("AddressLineText", ns.value_predicate, XSD.string, OWL.DatatypeProperty),
    ]
    for index, (local_name, predicate, range_iri, property_type) in enumerate(mappings):
        qname = schema_path[index]
        model.add((qname, RDF.type, LSM.QName))
        model.add((qname, LSM.namespace, Literal(xml_namespace)))
        model.add((qname, LSM.local_name, Literal(local_name)))
        model.add((qname, UAD_SCHEMA.sourceQName, Literal(f"{{{xml_namespace}}}{local_name}")))
        if index != missing_index:
            model.add((qname, UAD_SCHEMA.projectsTo, predicate))
            model.add((predicate, RDF.type, property_type))
            model.add((predicate, RDFS.range, range_iri))
    model.add((ns.property_class, RDF.type, OWL.Class))
    model.add((ns.address_class, RDF.type, OWL.Class))

    classified = Graph().parse(data=classified.serialize(format="turtle"), format="turtle")
    model = Graph().parse(data=model.serialize(format="turtle"), format="turtle")
    classified_before = set(classified)
    model_before = set(model)
    output = Graph()
    try:
        result = bind_governed_constraint_to_instance_rdf(
            classified_graph=classified,
            projection_model_graph=model,
            constraint_id=str(constraint),
            output_graph=output,
        )
    except ValueError as error:
        pytest.fail(
            "IT-55R3S1 requires governed EXCEPTION RDF identifying the "
            "unresolved schema resource and preserving its context, eligible "
            "for the Batch Results Graph. The binder instead raised an "
            f"uncontracted ValueError: {error}",
            pytrace=False,
        )

    assert set(classified) == classified_before
    assert set(model) == model_before
    assert classified_before.issubset(set(output))
    assert not list(output.objects(constraint, CV.instanceRdfBinding))
    assert not list(output.subjects(RDF.type, CV.InstanceRdfBinding))
    assert not list(output.subject_objects(CV.predicatePath))
    assert not list(output.objects(result.result_id, UADEX.stageKnowledge))

    record = read_construction_stage_result(
        exchange_graph=output, result_id=str(result.result_id)
    )
    assert record.constraint_id == str(constraint)
    assert record.construction_stage == "instance-rdf-binding"
    assert record.construction_status == "EXCEPTION"
    assert record.available_for_downstream is False
    assert record.exception_reason and record.exception_reason.strip()
    assert (result.result_id, UADEX.forConstraint, constraint) in output
    assert (result.result_id, CV.unresolvedLogicalSchemaResource, missing_resource) in output
    assert (result.result_id, CV.applicableContext, ns.context) in output
    assert (result.result_id, PROV.wasDerivedFrom, ns.source) in output

    added = set(output) - classified_before - model_before
    for subject, predicate, object_value in added:
        assert predicate != UAD_SCHEMA.projectsTo, "The binder invented a projection mapping."
        if predicate == RDF.type:
            assert object_value not in {
                OWL.Class, RDFS.Class, RDF.Property, OWL.ObjectProperty, OWL.DatatypeProperty
            }, "The binder invented an RDF class or predicate."
        assert predicate not in {CV.focusClass, CV.valuePredicate, CV.predicatePath}

    batch = Dataset().graph(ns.batch_results)
    for triple in output:
        batch.add(triple)
    restored = Graph().parse(data=batch.serialize(format="turtle"), format="turtle")
    assert isomorphic(batch, restored)
    assert read_construction_stage_result(
        exchange_graph=restored, result_id=str(result.result_id)
    ) == record
