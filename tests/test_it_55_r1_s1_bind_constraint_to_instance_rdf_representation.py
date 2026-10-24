"""IT-55R1S1: bind governed behavior to the established RDF projection."""

from __future__ import annotations

from importlib import import_module
from importlib.util import find_spec
from uuid import uuid4

import pytest
from rdflib import Graph, Literal, Namespace, RDF, RDFS, URIRef
from rdflib.collection import Collection
from rdflib.namespace import OWL, PROV, XSD

from app.services.constraint_behavior_classification import (
    classify_governed_constraint_behavior,
)
from app.services.construction_exchange import (
    UADEX,
    read_construction_stage_result,
)
from app.services.rdf_projection import RdfProjector, UAD_SCHEMA


CV = Namespace("https://dynamicontology.com/uad36/constraint-vocabulary#")
LSM = Namespace("https://dynamicontology.com/uad36/logical-schema#")
MODULE = "app.services.instance_rdf_binding_agent"


def _round_trip(graph: Graph) -> Graph:
    return Graph().parse(data=graph.serialize(format="turtle"), format="turtle")


@pytest.mark.parametrize("parent", ["PROPERTY", "BORROWER"], ids=["property", "borrower"])
def test_it_55_r1_s1_binds_constraint_to_one_instance_rdf_representation(
    parent: str,
) -> None:
    ns = Namespace(f"urn:uad36:test:it55r1s1:{uuid4().hex}:")
    xml_namespace = "urn:uad36:test:instance-binding:xml"
    constraint = ns.constraint
    context = ns.context
    behavior = ns.behavior
    source = ns.source
    schema_path = [ns.parent_qname, ns.address_qname, ns.value_qname]

    # Controlled projection-model fixture uses the metadata already consumed
    # by RdfProjector. Its RDF terms deliberately differ from XML local names.
    projection_model = Graph()
    mappings = [
        (schema_path[0], parent, ns.root_property, ns.root_class, OWL.ObjectProperty),
        (schema_path[1], "ADDRESS", ns.address_property, ns.address_class, OWL.ObjectProperty),
        (schema_path[2], "AddressLineText", ns.value_property, XSD.string, OWL.DatatypeProperty),
    ]
    for qname, local_name, predicate, range_iri, property_type in mappings:
        for triple in (
            (qname, RDF.type, LSM.QName),
            (qname, LSM.namespace, Literal(xml_namespace)),
            (qname, LSM.local_name, Literal(local_name)),
            (qname, UAD_SCHEMA.sourceQName, Literal(f"{{{xml_namespace}}}{local_name}")),
            (qname, UAD_SCHEMA.projectsTo, predicate),
            (predicate, RDF.type, property_type),
            (predicate, RDFS.range, range_iri),
        ):
            projection_model.add(triple)
    projection_model.add((ns.root_class, RDF.type, OWL.Class))
    projection_model.add((ns.address_class, RDF.type, OWL.Class))
    projection_model = _round_trip(projection_model)

    # This is an independent test oracle: construction never receives this
    # appraisal graph. A real projector confirms what the model represents.
    xml_bytes = (
        f'<{parent} xmlns="{xml_namespace}"><ADDRESS>'
        f'<AddressLineText>Test address</AddressLineText>'
        f'</ADDRESS></{parent}>'
    ).encode("utf-8")
    instance_graph = RdfProjector(ontology=projection_model).project(
        xml_bytes=xml_bytes,
        source_name=f"{uuid4().hex}.xml",
    )
    roots = set(instance_graph.subjects(RDF.type, ns.root_class))
    assert len(roots) == 1, "Projection fixture must produce one root resource."
    root = next(iter(roots))
    addresses = set(instance_graph.objects(root, ns.address_property))
    assert len(addresses) == 1
    address = next(iter(addresses))
    assert (address, RDF.type, ns.address_class) in instance_graph
    assert str(next(instance_graph.objects(address, ns.value_property))) == "Test address"

    requirement = Literal("Supply the address line in the governed context.")
    violation = Literal("The address line is absent in the governed context.")
    context_graph = Graph()
    for triple in (
        (constraint, RDF.type, CV.NormalizedConstraint),
        (constraint, CV.requirementText, requirement),
        (constraint, CV.violationCondition, violation),
        (constraint, CV.boundLogicalSchemaResource, schema_path[-1]),
        (constraint, CV.applicableContext, context),
        (constraint, PROV.wasDerivedFrom, source),
        (context, RDF.type, CV.ConstraintContext),
        (context, CV.schemaPath, ns.schema_path),
    ):
        context_graph.add(triple)
    Collection(context_graph, ns.schema_path, schema_path)
    registry = Graph()
    registry.add((behavior, RDF.type, CV.ValidationBehavior))
    registry.add((behavior, CV.requirementText, requirement))
    registry.add((behavior, CV.violationCondition, violation))
    classified = Graph()
    classify_governed_constraint_behavior(
        context_graph=context_graph,
        established_behaviors_graph=registry,
        constraint_id=str(constraint),
        output_graph=classified,
    )
    classified = _round_trip(classified)
    classifications = set(classified.objects(constraint, CV.behaviorClassification))
    assert len(classifications) == 1
    classification = next(iter(classifications))
    classified_before = set(classified)
    projection_before = set(projection_model)

    assert find_spec(MODULE) is not None, (
        "IT-55R1S1 requires app.services.instance_rdf_binding_agent to bind "
        "classified governed RDF to the established Instance RDF projection model."
    )
    operation = getattr(
        import_module(MODULE), "bind_governed_constraint_to_instance_rdf", None
    )
    assert callable(operation), (
        "IT-55R1S1 requires bind_governed_constraint_to_instance_rdf("
        "classified_graph=..., projection_model_graph=..., "
        "constraint_id=..., output_graph=...)."
    )
    output = Graph()
    result = operation(
        classified_graph=classified,
        projection_model_graph=projection_model,
        constraint_id=str(constraint),
        output_graph=output,
    )
    assert set(classified) == classified_before
    assert set(projection_model) == projection_before
    assert classified_before.issubset(set(output))

    downstream = _round_trip(output)
    bindings = set(downstream.objects(constraint, CV.instanceRdfBinding))
    assert len(bindings) == 1
    binding = next(iter(bindings))
    assert isinstance(binding, URIRef)
    assert (binding, RDF.type, CV.InstanceRdfBinding) in downstream
    assert set(downstream.objects(binding, CV.boundLogicalSchemaResource)) == {
        schema_path[-1]
    }
    assert set(downstream.objects(binding, CV.applicableContext)) == {context}
    assert set(downstream.objects(binding, CV.behaviorClassification)) == {classification}
    assert set(downstream.objects(binding, CV.validationBehavior)) == {behavior}
    assert set(downstream.objects(binding, CV.focusClass)) == {ns.root_class}
    assert set(downstream.objects(binding, CV.valuePredicate)) == {ns.value_property}
    paths = list(downstream.objects(binding, CV.predicatePath))
    assert len(paths) == 1
    assert list(Collection(downstream, paths[0])) == [
        ns.address_property,
        ns.value_property,
    ], "Binding must use the projector's exact predicates in governed path order."
    assert (binding, PROV.wasDerivedFrom, source) in downstream

    record = read_construction_stage_result(
        exchange_graph=downstream, result_id=str(result.result_id)
    )
    assert record.constraint_id == str(constraint)
    assert record.construction_stage == "instance-rdf-binding"
    assert record.construction_status == "GREEN"
    assert record.available_for_downstream is True
    assert (result.result_id, UADEX.stageKnowledge, binding) in downstream
