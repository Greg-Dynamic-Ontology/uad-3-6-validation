"""IT-56R2S1: preserve governed meaning independently of generated SHACL."""

from __future__ import annotations

from importlib import import_module
from importlib.util import find_spec
from pathlib import Path
from uuid import uuid4

from pyshacl import validate as _pyshacl_validate
from rdflib import Graph, Literal, Namespace, RDF, RDFS, URIRef
from rdflib.collection import Collection
from rdflib.compare import isomorphic
from rdflib.namespace import OWL, PROV, SH, XSD

from app.services.constraint_behavior_classification import classify_governed_constraint_behavior
from app.services.construction_exchange import UADEX, read_construction_stage_result
from app.services.instance_rdf_binding_agent import bind_governed_constraint_to_instance_rdf
from app.services.rdf_projection import RdfProjector, UAD_SCHEMA


CV = Namespace("https://dynamicontology.com/uad36/constraint-vocabulary#")
LSM = Namespace("https://dynamicontology.com/uad36/logical-schema#")
MODULE = "app.services.shacl_generation_agent"


def _validate(*, data_graph: Graph, shacl_graph: Graph):
    """Execute real validation without modifying the artifact comparison graph.

    pySHACL adds supporting vocabulary triples to its supplied shapes graph.
    Give the validator a separate copy; keep the generated artifact intact.
    """
    validation_shapes = Graph()
    for prefix, namespace in shacl_graph.namespaces():
        validation_shapes.bind(prefix, namespace)
    for triple in shacl_graph:
        validation_shapes.add(triple)
    return _pyshacl_validate(data_graph=data_graph, shacl_graph=validation_shapes)

def test_it_56_r2_s1_preserves_governed_meaning_independently_of_shacl(
    tmp_path: Path,
) -> None:
    ns = Namespace(f"urn:uad36:test:it56r2s1:{uuid4().hex}:")
    constraint = ns.constraint
    xml_namespace = "urn:uad36:test:shacl-generation:xml"
    requirement = Literal("Provide an address line for each property.")
    violation = Literal("A property has no address line.")
    schema_path = [ns.property_qname, ns.address_qname, ns.value_qname]
    context_graph = Graph()
    for triple in (
        (constraint, RDF.type, CV.NormalizedConstraint),
        (constraint, CV.requirementText, requirement),
        (constraint, CV.violationCondition, violation),
        (constraint, CV.boundLogicalSchemaResource, ns.value_qname),
        (constraint, CV.applicableContext, ns.context),
        (constraint, PROV.wasDerivedFrom, ns.source),
        (ns.context, RDF.type, CV.ConstraintContext),
        (ns.context, CV.schemaPath, ns.schema_path),
    ):
        context_graph.add(triple)
    Collection(context_graph, ns.schema_path, schema_path)

    registry = Graph()
    registry.add((ns.behavior, RDF.type, CV.ValidationBehavior))
    registry.add((ns.behavior, CV.requirementText, requirement))
    registry.add((ns.behavior, CV.violationCondition, violation))
    classified = Graph()
    classify_governed_constraint_behavior(
        context_graph=context_graph,
        established_behaviors_graph=registry,
        constraint_id=str(constraint),
        output_graph=classified,
    )

    model = Graph()
    for qname, local_name, predicate, range_iri, property_type in (
        (ns.property_qname, "PROPERTY", ns.property_predicate, ns.property_class, OWL.ObjectProperty),
        (ns.address_qname, "ADDRESS", ns.address_predicate, ns.address_class, OWL.ObjectProperty),
        (ns.value_qname, "AddressLineText", ns.value_predicate, XSD.string, OWL.DatatypeProperty),
    ):
        for triple in (
            (qname, RDF.type, LSM.QName),
            (qname, LSM.namespace, Literal(xml_namespace)),
            (qname, LSM.local_name, Literal(local_name)),
            (qname, UAD_SCHEMA.sourceQName, Literal(f"{{{xml_namespace}}}{local_name}")),
            (qname, UAD_SCHEMA.projectsTo, predicate),
            (predicate, RDF.type, property_type),
            (predicate, RDFS.range, range_iri),
        ):
            model.add(triple)
    model.add((ns.property_class, RDF.type, OWL.Class))
    model.add((ns.address_class, RDF.type, OWL.Class))
    bound = Graph()
    bind_governed_constraint_to_instance_rdf(
        classified_graph=classified,
        projection_model_graph=model,
        constraint_id=str(constraint),
        output_graph=bound,
    )

    # The governed implementation registry, not English-text guessing, supplies
    # the established SHACL component for this behavior.
    patterns = Graph()
    patterns.add((ns.behavior, CV.shaclImplementationPattern, ns.pattern))
    patterns.add((ns.pattern, RDF.type, CV.ShaclImplementationPattern))
    patterns.add((ns.pattern, CV.propertyShapeTemplate, ns.template))
    patterns.add((ns.template, RDF.type, SH.PropertyShape))
    patterns.add((ns.template, SH.minCount, Literal(1)))
    bound = Graph().parse(data=bound.serialize(format="turtle"), format="turtle")
    patterns = Graph().parse(data=patterns.serialize(format="turtle"), format="turtle")
    bound_before = set(bound)
    patterns_before = set(patterns)

    assert find_spec(MODULE) is not None, (
        "IT-56R2S1 requires app.services.shacl_generation_agent to derive "
        "and write executable SHACL from governed behavior, an established "
        "implementation pattern, and the Instance RDF binding."
    )
    generate = getattr(import_module(MODULE), "generate_governed_constraint_shacl", None)
    assert callable(generate), (
        "IT-56R2S1 requires generate_governed_constraint_shacl(bound_graph=..., "
        "implementation_patterns_graph=..., constraint_id=..., "
        "output_path=..., output_graph=...)."
    )

    # A caller-selected project artifact destination is redirected into the
    # pytest temporary directory. Only the PRODUCTION operation writes it.
    output_path = tmp_path / "governed-shapes" / "constraint.ttl"
    assert not output_path.exists()
    output = Graph()
    result = generate(
        bound_graph=bound,
        implementation_patterns_graph=patterns,
        constraint_id=str(constraint),
        output_path=output_path,
        output_graph=output,
    )
    assert set(bound) == bound_before
    assert set(patterns) == patterns_before
    assert bound_before.issubset(set(output))
    assert output_path.is_file(), "The production generator must write its SHACL artifact."
    shapes = Graph().parse(output_path, format="turtle")
    representations = set(output.objects(constraint, CV.shaclRepresentation))
    assert len(representations) == 1
    shape = next(iter(representations))
    assert isinstance(shape, URIRef)
    assert set(shapes.subjects(RDF.type, SH.NodeShape)) == {shape}
    assert (shape, CV.implementsConstraint, constraint) in shapes
    assert (shape, PROV.wasDerivedFrom, ns.source) in shapes
    assert (shape, PROV.wasDerivedFrom, ns.pattern) in shapes
    assert set(shapes.objects(shape, SH.targetClass)) == {ns.property_class}
    properties = set(shapes.objects(shape, SH.property))
    assert len(properties) == 1
    property_shape = next(iter(properties))
    assert set(shapes.objects(property_shape, SH.minCount)) == {Literal(1)}
    assert requirement in set(shapes.objects(property_shape, SH.message))
    paths = list(shapes.objects(property_shape, SH.path))
    assert len(paths) == 1
    assert list(Collection(shapes, paths[0])) == [ns.address_predicate, ns.value_predicate]
    assert (shape, RDF.type, SH.NodeShape) in output

    for supplied, expected_conformance in ((True, True), (False, False)):
        value = "Test address" if supplied else ""
        xml_bytes = (
            f'<PROPERTY xmlns="{xml_namespace}"><ADDRESS>'
            f'<AddressLineText>{value}</AddressLineText></ADDRESS></PROPERTY>'
        ).encode("utf-8")
        instance = RdfProjector(ontology=model).project(
            xml_bytes=xml_bytes, source_name=f"{uuid4().hex}.xml"
        )
        conforms, report, _ = _validate(data_graph=instance, shacl_graph=shapes)
        assert bool(conforms) is expected_conformance
        if not supplied:
            findings = set(report.subjects(RDF.type, SH.ValidationResult))
            assert len(findings) == 1
            finding = next(iter(findings))
            assert (finding, SH.sourceShape, property_shape) in report
            assert requirement in set(report.objects(finding, SH.resultMessage))

    record = read_construction_stage_result(
        exchange_graph=output, result_id=str(result.result_id)
    )
    assert record.constraint_id == str(constraint)
    assert record.construction_stage == "shacl-representation"
    assert record.construction_status == "GREEN"
    assert record.available_for_downstream is True
    assert (result.result_id, UADEX.stageKnowledge, shape) in output

    classification = next(bound.objects(constraint, CV.behaviorClassification))
    binding = next(bound.objects(constraint, CV.instanceRdfBinding))
    governed_resources = (constraint, ns.behavior, ns.context, classification, binding)
    for resource in governed_resources:
        # Recording the derived representation may add its link, but it must
        # not rewrite the source resource or attach SHACL semantics to it.
        assert {
            (predicate, value)
            for predicate, value in output.predicate_objects(resource)
            if predicate != CV.shaclRepresentation
        } == set(bound.predicate_objects(resource))
        assert not any(
            str(predicate).startswith(str(SH))
            for predicate, _ in output.predicate_objects(resource)
        )
    assert (shape, CV.implementsConstraint, constraint) in shapes
    assert (shape, PROV.wasDerivedFrom, binding) in shapes
    assert set(output.objects(constraint, CV.requirementText)) == {requirement}
    assert set(output.objects(constraint, CV.violationCondition)) == {violation}

    # Change only an in-memory executable copy. This intentionally changes its
    # validation behavior, but cannot redefine governed meaning or its pattern.
    altered_shapes = Graph()
    for triple in shapes:
        altered_shapes.add(triple)
    altered_shapes.set((property_shape, SH.minCount, Literal(9)))
    valid_xml = (
        f'<PROPERTY xmlns="{xml_namespace}"><ADDRESS>'
        '<AddressLineText>Test address</AddressLineText></ADDRESS></PROPERTY>'
    ).encode("utf-8")
    valid_instance = RdfProjector(ontology=model).project(
        xml_bytes=valid_xml, source_name=f"{uuid4().hex}.xml"
    )
    altered_conforms, _, _ = _validate(
        data_graph=valid_instance, shacl_graph=altered_shapes
    )
    assert not altered_conforms
    assert set(bound) == bound_before
    assert set(patterns) == patterns_before
    assert set(patterns.objects(ns.template, SH.minCount)) == {Literal(1)}

    # Regenerate through production code using the SAME authoritative input.
    # The test never writes the SHACL artifact itself.
    regenerated_output = Graph()
    regenerated_result = generate(
        bound_graph=bound,
        implementation_patterns_graph=patterns,
        constraint_id=str(constraint),
        output_path=output_path,
        output_graph=regenerated_output,
    )
    regenerated_shapes = Graph().parse(output_path, format="turtle")
    assert isomorphic(regenerated_shapes, shapes), (
        "Authoritative governed knowledge must reproduce the original shape."
    )
    regenerated_conforms, _, _ = _validate(
        data_graph=valid_instance, shacl_graph=regenerated_shapes
    )
    assert regenerated_conforms
    assert set(bound) == bound_before
    assert set(patterns) == patterns_before
    assert read_construction_stage_result(
        exchange_graph=regenerated_output,
        result_id=str(regenerated_result.result_id),
    ).construction_status == "GREEN"