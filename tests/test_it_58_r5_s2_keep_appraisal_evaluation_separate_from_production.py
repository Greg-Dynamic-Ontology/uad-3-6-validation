"""IT-58R5S2: construct reusable artifacts separately from appraisal evaluation."""

from __future__ import annotations

import csv
from importlib import import_module
from pathlib import Path
from uuid import uuid4

import pytest
from rdflib import Graph, Literal, Namespace, RDF, RDFS, URIRef
from rdflib.namespace import OWL, PROV, SH, XSD

from app.models.schema_model import (
    ComplexTypeDefinition, ElementDeclaration, ModelGroup, ModelGroupKind,
    QName, SchemaModel,
)
from app.services.construction_exchange import (
    UADEX, read_construction_stage_result,
)
from app.services.governed_constraint_source_reader import EXPECTED_COLUMNS
from app.services.logical_schema_serializer import logical_schema_model_to_graph
from app.services.rdf_projection import RdfProjector, UAD_SCHEMA


CV = Namespace("https://dynamicontology.com/uad36/constraint-vocabulary#")
CFG = Namespace("https://dynamicontology.com/uad36/configuration#")
LSM = Namespace("https://dynamicontology.com/uad36/logical-schema#")
def _models(ns: Namespace) -> tuple[Graph, Graph]:
    xml_namespace = "urn:uad36:test:all-rows-pipeline:xml"

    def qname(name: str) -> QName:
        return QName(xml_namespace, name)

    value = ElementDeclaration(name=qname("AddressLineText"))
    address = ElementDeclaration(name=qname("ADDRESS"), type_name=qname("ADDRESS_TYPE"))
    root = ElementDeclaration(name=qname("PROPERTY"), type_name=qname("PROPERTY_TYPE"))
    address_type = ComplexTypeDefinition(
        name=qname("ADDRESS_TYPE"),
        content=ModelGroup(kind=ModelGroupKind.SEQUENCE, elements=(value,)),
    )
    property_type = ComplexTypeDefinition(
        name=qname("PROPERTY_TYPE"),
        content=ModelGroup(kind=ModelGroupKind.SEQUENCE, elements=(address,)),
    )
    schema = logical_schema_model_to_graph(SchemaModel(
        target_namespace=xml_namespace,
        elements={root.name: root},
        complex_types={item.name: item for item in (address_type, property_type)},
    ))
    projection = Graph()
    for triple in schema:
        projection.add(triple)
    for local_name, predicate, range_iri, property_type_iri in (
        ("PROPERTY", ns.property_predicate, ns.property_class, OWL.ObjectProperty),
        ("ADDRESS", ns.address_predicate, ns.address_class, OWL.ObjectProperty),
        ("AddressLineText", ns.value_predicate, XSD.string, OWL.DatatypeProperty),
    ):
        names = {
            subject for subject in schema.subjects(LSM.local_name, Literal(local_name))
            if (subject, RDF.type, LSM.QName) in schema
        }
        assert len(names) == 1
        resource = next(iter(names))
        assert isinstance(resource, URIRef)
        projection.add((resource, UAD_SCHEMA.sourceQName,
                        Literal(f"{{{xml_namespace}}}{local_name}")))
        projection.add((resource, UAD_SCHEMA.projectsTo, predicate))
        projection.add((predicate, RDF.type, property_type_iri))
        projection.add((predicate, RDFS.range, range_iri))
    projection.add((ns.property_class, RDF.type, OWL.Class))
    projection.add((ns.address_class, RDF.type, OWL.Class))
    return schema, projection


def test_it_58_r5_s2_keeps_appraisal_evaluation_separate_from_constraint_production(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pipeline = import_module("app.services.constraint_production_pipeline")
    shacl_engine = import_module("pyshacl")
    finding_service = import_module("app.services.validation_finding_projection")
    ns = Namespace(f"urn:uad36:test:it58r5s2:{uuid4().hex}:")
    unique_id = "0" + uuid4().hex
    requirement = "Provide the address line for each property."
    violation = "The property address line is absent."
    row = dict.fromkeys(EXPECTED_COLUMNS, "")
    row.update({
        "Unique ID": unique_id,
        "Primary Data Element": "AddressLineText",
        "Message ID": "test-rule-" + uuid4().hex,
        "Message Text": requirement,
        "Rule Logic": violation,
        "Severity": "Fatal",
        "Property Affected": "/PROPERTY/ADDRESS/AddressLineText",
        "Data Point Name / Value": "AddressLineText",
        " xPath": "/PROPERTY/ADDRESS/AddressLineText",
    })
    source_path = tmp_path / "constraints.csv"
    with source_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=EXPECTED_COLUMNS)
        writer.writeheader()
        writer.writerow(row)
    source_iri = URIRef(f"urn:uad36:governed-source:{source_path.name}#row=2")
    configuration = Graph()
    for triple in (
        (ns.configuration, RDF.type, CFG.ApplicationConfiguration),
        (ns.configuration, CFG.hasSourceWorkbooks, ns.collection),
        (ns.configuration, CFG.activeComplianceSource, ns.source),
        (ns.collection, RDF.type, CFG.GovernedSourceWorkbookCollection),
        (ns.collection, CFG.containsWorkbook, ns.source),
        (ns.source, RDF.type, CFG.GovernedSourceArtifact),
        (ns.source, CFG.sourceFileLocation, Literal(str(source_path))),
        (ns.source, CFG.sourceFormat, Literal("csv")),
    ):
        configuration.add(triple)
    configuration_path = tmp_path / "configuration.ttl"
    configuration.serialize(destination=configuration_path, format="turtle")
    schema, projection = _models(ns)
    behaviors = Graph()
    for triple in (
        (ns.behavior, RDF.type, CV.ValidationBehavior),
        (ns.behavior, CV.requirementText, Literal(requirement)),
        (ns.behavior, CV.violationCondition, Literal(violation)),
    ):
        behaviors.add(triple)
    patterns = Graph()
    for triple in (
        (ns.behavior, CV.shaclImplementationPattern, ns.pattern),
        (ns.pattern, RDF.type, CV.ShaclImplementationPattern),
        (ns.pattern, CV.propertyShapeTemplate, ns.template),
        (ns.template, RDF.type, SH.PropertyShape),
        (ns.template, SH.minCount, Literal(1)),
    ):
        patterns.add(triple)
    original_inputs = [set(graph) for graph in (schema, projection, behaviors, patterns)]
    original_source = source_path.read_bytes()
    original_configuration = configuration_path.read_bytes()

    def forbidden_runtime_call(*args, **kwargs):
        pytest.fail("Constraint production invoked appraisal evaluation or runtime finding projection.")

    output_directory = tmp_path / "production-artifacts"
    batch_path = tmp_path / "batch-state" / "results.ttl"
    # No XML report exists or is supplied during construction. Fail immediately
    # if construction tries the projector, SHACL evaluator, or IT-57 projector.
    with monkeypatch.context() as construction_only:
        construction_only.setattr(RdfProjector, "project", forbidden_runtime_call)
        for module, operation_name in (
            (shacl_engine, "validate"),
            (finding_service, "project_governed_findings"),
        ):
            real = getattr(module, operation_name)
            construction_only.setattr(module, operation_name, forbidden_runtime_call)
            if getattr(pipeline, operation_name, None) is real:
                construction_only.setattr(pipeline, operation_name, forbidden_runtime_call)
        result = pipeline.process_governed_source_row(
            configuration_path=configuration_path,
            unique_id=unique_id,
            logical_schema_graph=schema,
            projection_model_graph=projection,
            established_behaviors_graph=behaviors,
            implementation_patterns_graph=patterns,
            output_directory=output_directory,
            batch_results_path=batch_path,
        )
    assert result.is_complete is True
    constraint = URIRef(result.constraint_id)
    rdf_path, shacl_path = Path(result.rdf_path), Path(result.shacl_path)
    for path in (rdf_path, shacl_path):
        assert path.is_file()
        assert path.resolve().is_relative_to(output_directory.resolve())
    governed = Graph().parse(rdf_path, format="turtle")
    shapes = Graph().parse(shacl_path, format="turtle")
    batch = Graph().parse(batch_path, format="turtle")
    assert (constraint, RDF.type, CV.NormalizedConstraint) in governed
    assert (constraint, PROV.wasDerivedFrom, source_iri) in governed
    shape_ids = set(shapes.subjects(RDF.type, SH.NodeShape))
    assert len(shape_ids) == 1
    shape = next(iter(shape_ids))
    assert (shape, CV.implementsConstraint, constraint) in shapes
    assert (shape, PROV.wasDerivedFrom, source_iri) in shapes
    for graph in (governed, shapes, batch):
        assert not list(graph.subjects(RDF.type, SH.ValidationReport))
        assert not list(graph.subjects(RDF.type, SH.ValidationResult))
        assert not list(graph.subjects(RDF.type, CV.ReportFindingException))
    records = [
        read_construction_stage_result(exchange_graph=batch, result_id=str(node))
        for node in batch.subjects(UADEX.forConstraint, constraint)
    ]
    assert len(records) == 6
    assert all(record.construction_status == "GREEN" and record.available_for_downstream
               for record in records)
    saved_artifacts = {path: path.read_bytes() for path in (rdf_path, shacl_path, batch_path)}

    # IT-57 also consumes governed finding knowledge. Supply that knowledge
    # explicitly as a separate fixture; do not infer it from SHACL or require
    # the construction coordinator to manufacture finding metadata.
    finding_knowledge = Graph()
    for triple in governed:
        finding_knowledge.add(triple)
    for triple in (
        (constraint, CV.sourceConstraint, source_iri),
        (constraint, CV.umdpRule, ns.governed_rule),
        (constraint, CV.violationKind, ns.MissingRequiredValue),
        (ns.governed_rule, CV.sourceRuleId, Literal(row["Message ID"])),
        (ns.governed_rule, PROV.wasDerivedFrom, source_iri),
    ):
        finding_knowledge.add(triple)
    finding_knowledge_before = set(finding_knowledge)

    # Only after construction completes do two independent appraisal inputs
    # arrive. Both use the same persisted artifacts without reconstructing them.
    xml_namespace = "urn:uad36:test:all-rows-pipeline:xml"
    for label, content, expected_conforms in (
        ("supplied-address", "<ADDRESS><AddressLineText>123 Test Street</AddressLineText></ADDRESS>", True),
        ("missing-address", "", False),
    ):
        xml_bytes = f'<PROPERTY xmlns="{xml_namespace}">{content}</PROPERTY>'.encode("utf-8")
        instance = RdfProjector(ontology=projection).project(
            xml_bytes=xml_bytes, source_name=f"{label}.xml",
        )
        # pySHACL may enrich its in-memory shapes graph. Reload a fresh copy
        # of the same saved shapes for each independent evaluation.
        conforms, report, _ = shacl_engine.validate(
            data_graph=instance,
            shacl_graph=Graph().parse(shacl_path, format="turtle"),
        )
        assert bool(conforms) is expected_conforms
        results = set(report.subjects(RDF.type, SH.ValidationResult))
        assert len(results) == (0 if expected_conforms else 1)
        projected = finding_service.project_governed_findings(
            shacl_result_graph=report,
            governed_constraint_graph=finding_knowledge,
        )
        assert len(projected.exception_graph) == 0
        assert len(projected.findings) == (0 if expected_conforms else 1)
        if not expected_conforms:
            finding = projected.findings[0]
            assert finding.governed_constraint == constraint
            assert finding.source_constraint == source_iri
            assert finding.umdp_rule == ns.governed_rule
            assert finding.violation_kind == ns.MissingRequiredValue
            assert finding.severity == "Fatal"
            assert finding.shacl_validation_result in results
            assert (finding.shacl_validation_result, SH.focusNode, finding.focus_node) in report
        assert set(finding_knowledge) == finding_knowledge_before
    assert {path: path.read_bytes() for path in saved_artifacts} == saved_artifacts
    assert source_path.read_bytes() == original_source
    assert configuration_path.read_bytes() == original_configuration
    assert [set(graph) for graph in (schema, projection, behaviors, patterns)] == original_inputs


