"""IT-56R3S1: reuse one pattern without merging constraint-specific knowledge."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from pyshacl import validate
from rdflib import Graph, Literal, Namespace, RDF, RDFS
from rdflib.collection import Collection
from rdflib.namespace import OWL, PROV, SH, XSD

from app.services.constraint_behavior_classification import classify_governed_constraint_behavior
from app.services.construction_exchange import UADEX, read_construction_stage_result
from app.services.instance_rdf_binding_agent import bind_governed_constraint_to_instance_rdf
from app.services.rdf_projection import RdfProjector, UAD_SCHEMA
from app.services.shacl_generation_agent import generate_governed_constraint_shacl


CV = Namespace("https://dynamicontology.com/uad36/constraint-vocabulary#")
LSM = Namespace("https://dynamicontology.com/uad36/logical-schema#")


def test_it_56_r3_s1_reuses_pattern_for_constraint_specific_shacl(tmp_path: Path) -> None:
    ns = Namespace(f"urn:uad36:test:it56r3s1:{uuid4().hex}:")
    xml_namespace = "urn:uad36:test:shared-shacl-pattern:xml"
    requirement = Literal("Supply the governed value in its applicable context.")
    violation = Literal("The governed value is absent in its applicable context.")
    behavior = ns.behavior
    pattern = ns.pattern
    registry = Graph()
    registry.add((behavior, RDF.type, CV.ValidationBehavior))
    registry.add((behavior, CV.requirementText, requirement))
    registry.add((behavior, CV.violationCondition, violation))
    patterns = Graph()
    patterns.add((behavior, CV.shaclImplementationPattern, pattern))
    patterns.add((pattern, RDF.type, CV.ShaclImplementationPattern))
    patterns.add((pattern, CV.propertyShapeTemplate, ns.template))
    patterns.add((ns.template, RDF.type, SH.PropertyShape))
    patterns.add((ns.template, SH.minCount, Literal(1)))
    pattern_before = set(patterns)
    registry_before = set(registry)
    records = []

    # Different paths and target classes prevent a shared pattern from hiding
    # accidental reuse of the first constraint's context or Instance RDF binding.
    for case, root_name, container_name, value_name in (
        ("property", "PROPERTY", "ADDRESS", "AddressLineText"),
        ("borrower", "BORROWER", "CONTACT", "FullName"),
    ):
        constraint = ns[f"{case}-constraint"]
        source = ns[f"{case}-source"]
        context = ns[f"{case}-context"]
        qnames = [ns[f"{case}-qname-{index}"] for index in range(3)]
        predicates = [ns[f"{case}-predicate-{index}"] for index in range(3)]
        root_class = ns[f"{case}-root-class"]
        container_class = ns[f"{case}-container-class"]
        model = Graph()
        for index, (local_name, range_iri, property_type) in enumerate((
            (root_name, root_class, OWL.ObjectProperty),
            (container_name, container_class, OWL.ObjectProperty),
            (value_name, XSD.string, OWL.DatatypeProperty),
        )):
            for triple in (
                (qnames[index], RDF.type, LSM.QName),
                (qnames[index], LSM.namespace, Literal(xml_namespace)),
                (qnames[index], LSM.local_name, Literal(local_name)),
                (qnames[index], UAD_SCHEMA.sourceQName, Literal(f"{{{xml_namespace}}}{local_name}")),
                (qnames[index], UAD_SCHEMA.projectsTo, predicates[index]),
                (predicates[index], RDF.type, property_type),
                (predicates[index], RDFS.range, range_iri),
            ):
                model.add(triple)
        model.add((root_class, RDF.type, OWL.Class))
        model.add((container_class, RDF.type, OWL.Class))

        upstream = Graph()
        for triple in (
            (constraint, RDF.type, CV.NormalizedConstraint),
            (constraint, CV.requirementText, requirement),
            (constraint, CV.violationCondition, violation),
            (constraint, CV.boundLogicalSchemaResource, qnames[-1]),
            (constraint, CV.applicableContext, context),
            (constraint, PROV.wasDerivedFrom, source),
            (context, RDF.type, CV.ConstraintContext),
            (context, CV.schemaPath, ns[f"{case}-schema-path"]),
        ):
            upstream.add(triple)
        Collection(upstream, ns[f"{case}-schema-path"], qnames)
        classified = Graph()
        classify_governed_constraint_behavior(
            context_graph=upstream,
            established_behaviors_graph=registry,
            constraint_id=str(constraint),
            output_graph=classified,
        )
        bound = Graph()
        bind_governed_constraint_to_instance_rdf(
            classified_graph=classified,
            projection_model_graph=model,
            constraint_id=str(constraint),
            output_graph=bound,
        )
        bound_before = set(bound)
        binding = next(bound.objects(constraint, CV.instanceRdfBinding))
        output = Graph()
        artifact = tmp_path / "governed-shapes" / f"{case}.ttl"
        result = generate_governed_constraint_shacl(
            bound_graph=bound,
            implementation_patterns_graph=patterns,
            constraint_id=str(constraint),
            output_path=artifact,
            output_graph=output,
        )
        assert artifact.is_file(), "Production code must persist each shape."
        shapes = Graph().parse(artifact, format="turtle")
        assert set(bound) == bound_before
        assert bound_before.issubset(set(output))
        assert set(patterns) == pattern_before
        assert set(registry) == registry_before
        representations = set(output.objects(constraint, CV.shaclRepresentation))
        assert len(representations) == 1
        shape = next(iter(representations))
        assert set(shapes.subjects(RDF.type, SH.NodeShape)) == {shape}
        assert (shape, CV.implementsConstraint, constraint) in shapes
        assert (shape, PROV.wasDerivedFrom, source) in shapes
        assert (shape, PROV.wasDerivedFrom, pattern) in shapes
        assert (shape, PROV.wasDerivedFrom, binding) in shapes
        assert set(shapes.objects(shape, SH.targetClass)) == {root_class}
        properties = list(shapes.objects(shape, SH.property))
        assert len(properties) == 1
        property_shape = properties[0]
        heads = list(shapes.objects(property_shape, SH.path))
        assert len(heads) == 1
        assert list(Collection(shapes, heads[0])) == predicates[1:]
        assert set(shapes.objects(property_shape, SH.minCount)) == {Literal(1)}
        assert set(shapes.objects(property_shape, SH.message)) == {requirement}
        assert set(output.objects(constraint, CV.applicableContext)) == {context}
        assert set(output.objects(constraint, CV.instanceRdfBinding)) == {binding}

        record = read_construction_stage_result(
            exchange_graph=output, result_id=str(result.result_id)
        )
        assert record.constraint_id == str(constraint)
        assert record.construction_status == "GREEN"
        assert record.available_for_downstream is True
        assert (result.result_id, UADEX.stageKnowledge, shape) in output

        for supplied in (True, False):
            value = "Supplied value" if supplied else ""
            xml_bytes = (
                f'<{root_name} xmlns="{xml_namespace}"><{container_name}>'
                f'<{value_name}>{value}</{value_name}>'
                f'</{container_name}></{root_name}>'
            ).encode("utf-8")
            instance = RdfProjector(ontology=model).project(
                xml_bytes=xml_bytes, source_name=f"{uuid4().hex}.xml"
            )
            # pySHACL mutates its supplied shapes graph; validate a fresh
            # parsed artifact so the comparison graph remains unchanged.
            conforms, _, _ = validate(
                data_graph=instance,
                shacl_graph=Graph().parse(artifact, format="turtle"),
            )
            assert bool(conforms) is supplied
        records.append((constraint, source, context, binding, shape, property_shape, shapes))

    first, second = records
    assert all(first[index] != second[index] for index in range(6))
    for own, other in ((first, second), (second, first)):
        own_shape, own_graph = own[4], own[6]
        assert (own_shape, CV.implementsConstraint, other[0]) not in own_graph
        assert (own_shape, PROV.wasDerivedFrom, other[1]) not in own_graph
        assert (own_shape, PROV.wasDerivedFrom, other[3]) not in own_graph
    assert set(patterns) == pattern_before
