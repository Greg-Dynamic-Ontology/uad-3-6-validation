"""IT-55R3S2: record incompatible Instance RDF bindings for review."""

from __future__ import annotations

from uuid import uuid4

import pytest
from rdflib import Graph, Literal, Namespace, RDF, RDFS, URIRef
from rdflib.collection import Collection
from rdflib.namespace import OWL, PROV, XSD

from app.services.construction_exchange import UADEX, read_construction_stage_result
from app.services.instance_rdf_binding_agent import bind_governed_constraint_to_instance_rdf
from app.services.rdf_projection import UAD_SCHEMA


CV = Namespace("https://dynamicontology.com/uad36/constraint-vocabulary#")
LSM = Namespace("https://dynamicontology.com/uad36/logical-schema#")


def _round_trip(graph: Graph) -> Graph:
    return Graph().parse(data=graph.serialize(format="turtle"), format="turtle")


@pytest.mark.parametrize(
    "ambiguous_index", [1, 2], ids=["context-predicate", "value-predicate"]
)
@pytest.mark.parametrize("reverse_order", [False, True], ids=["forward", "reverse"])
def test_it_55_r3_s2_rejects_ambiguous_instance_rdf_binding(
    ambiguous_index: int,
    reverse_order: bool,
) -> None:
    ns = Namespace(f"urn:uad36:test:it55r3s2:{uuid4().hex}:")
    constraint = ns.constraint
    schema_path = [ns.property_qname, ns.address_qname, ns.value_qname]
    xml_namespace = "urn:uad36:test:ambiguous-binding:xml"
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
    alternate = ns.alternate_predicate
    for index, (local_name, predicate, range_iri, property_type) in enumerate(mappings):
        qname = schema_path[index]
        model.add((qname, RDF.type, LSM.QName))
        model.add((qname, LSM.namespace, Literal(xml_namespace)))
        model.add((qname, LSM.local_name, Literal(local_name)))
        model.add((qname, UAD_SCHEMA.sourceQName, Literal(f"{{{xml_namespace}}}{local_name}")))
        terms = [predicate, alternate] if index == ambiguous_index else [predicate]
        for term in reversed(terms) if reverse_order else terms:
            model.add((qname, UAD_SCHEMA.projectsTo, term))
            model.add((term, RDF.type, property_type))
            model.add((term, RDFS.range, range_iri))
    model.add((ns.property_class, RDF.type, OWL.Class))
    model.add((ns.address_class, RDF.type, OWL.Class))
    model.add((mappings[ambiguous_index][1], OWL.differentFrom, alternate))

    classified = _round_trip(classified)
    model = _round_trip(model)
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
            "IT-55R3S2 requires governed EXCEPTION RDF recording the candidate "
            "Instance RDF bindings and routing the constraint for review. "
            f"The binder raised an uncontracted ValueError: {error}",
            pytrace=False,
        )

    assert set(classified) == classified_before
    assert set(model) == model_before
    assert classified_before.issubset(set(output))
    assert not list(output.objects(constraint, CV.instanceRdfBinding))
    assert not list(output.subjects(RDF.type, CV.InstanceRdfBinding))
    assert not list(output.objects(result.result_id, UADEX.stageKnowledge))

    downstream = _round_trip(output)
    record = read_construction_stage_result(
        exchange_graph=downstream, result_id=str(result.result_id)
    )
    assert record.constraint_id == str(constraint)
    assert record.construction_stage == "instance-rdf-binding"
    assert record.construction_status == "EXCEPTION"
    assert record.available_for_downstream is False
    assert record.requires_review is True
    assert record.exception_reason and record.exception_reason.strip()
    assert (result.result_id, UADEX.forConstraint, constraint) in downstream
    assert (result.result_id, CV.applicableContext, ns.context) in downstream
    assert (result.result_id, PROV.wasDerivedFrom, ns.source) in downstream

    candidates = set(downstream.objects(result.result_id, CV.candidateInstanceRdfBinding))
    assert len(candidates) == 2, "Record both complete candidate bindings for review."
    actual_paths = set()
    for candidate in candidates:
        assert isinstance(candidate, URIRef)
        assert (candidate, RDF.type, CV.CandidateInstanceRdfBinding) in downstream
        assert set(downstream.objects(candidate, CV.focusClass)) == {ns.property_class}
        assert set(downstream.objects(candidate, CV.applicableContext)) == {ns.context}
        assert set(downstream.objects(candidate, CV.boundLogicalSchemaResource)) == {
            schema_path[-1]
        }
        assert set(downstream.objects(candidate, CV.behaviorClassification)) == {
            ns.classification
        }
        heads = list(downstream.objects(candidate, CV.predicatePath))
        assert len(heads) == 1
        path = tuple(Collection(downstream, heads[0]))
        actual_paths.add(path)
        assert set(downstream.objects(candidate, CV.valuePredicate)) == {path[-1]}

    alternative_path = (
        (alternate, ns.value_predicate)
        if ambiguous_index == 1
        else (ns.address_predicate, alternate)
    )
    assert actual_paths == {
        (ns.address_predicate, ns.value_predicate),
        alternative_path,
    }, "Candidates must retain the established predicates in governed path order."
