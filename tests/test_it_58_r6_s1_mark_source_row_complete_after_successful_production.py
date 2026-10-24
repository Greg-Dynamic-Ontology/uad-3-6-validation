"""IT-58R6S1: persist completion only with verified reusable artifacts."""

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


def test_it_58_r6_s1_persists_completed_production_state_with_verified_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pipeline = import_module("app.services.constraint_production_pipeline")
    ns = Namespace(f"urn:uad36:test:it58r6s1:{uuid4().hex}:")
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
    original_files = (source_path.read_bytes(), configuration_path.read_bytes())
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
    model_inputs = (schema, projection, behaviors, patterns)
    originals = [set(graph) for graph in model_inputs]

    def no_runtime_evaluation(*args, **kwargs):
        pytest.fail("Production completion must not depend on appraisal evaluation or runtime findings.")

    monkeypatch.setattr(RdfProjector, "project", no_runtime_evaluation)
    for module_name, operation_name in (
        ("pyshacl", "validate"),
        ("app.services.validation_finding_projection", "project_governed_findings"),
    ):
        module = import_module(module_name)
        real = getattr(module, operation_name)
        monkeypatch.setattr(module, operation_name, no_runtime_evaluation)
        if getattr(pipeline, operation_name, None) is real:
            monkeypatch.setattr(pipeline, operation_name, no_runtime_evaluation)
    output_directory = tmp_path / "production-artifacts"
    batch_path = tmp_path / "batch-state" / "results.ttl"
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
    assert result.unique_id == unique_id
    constraint = URIRef(result.constraint_id)
    rdf_path, shacl_path = Path(result.rdf_path), Path(result.shacl_path)
    for artifact in (rdf_path, shacl_path):
        assert artifact.is_file()
        assert artifact.resolve().is_relative_to(output_directory.resolve())
    rdf = Graph().parse(rdf_path, format="turtle")
    shapes = Graph().parse(shacl_path, format="turtle")
    assert set(rdf.objects(constraint, CV.governedUniqueId)) == {Literal(unique_id)}
    assert (constraint, PROV.wasDerivedFrom, source_iri) in rdf
    shape_ids = set(shapes.subjects(RDF.type, SH.NodeShape))
    assert len(shape_ids) == 1
    shape = next(iter(shape_ids))
    assert (shape, CV.implementsConstraint, constraint) in shapes
    assert (shape, PROV.wasDerivedFrom, source_iri) in shapes
    # Reopen the saved batch graph: a returned Boolean alone cannot prove
    # that completion survives process exit or identifies its evidence.
    batch = Graph().parse(batch_path, format="turtle")
    records = [
        read_construction_stage_result(exchange_graph=batch, result_id=str(node))
        for node in batch.subjects(UADEX.forConstraint, constraint)
    ]
    expected_stages = {
        "normalized-constraint-representation",
        "logical-schema-binding",
        "context-resolution",
        "validation-behavior",
        "instance-rdf-binding",
        "shacl-representation",
    }
    assert len(records) == len(expected_stages)
    assert {record.construction_stage for record in records} == expected_stages
    assert all(record.construction_status == "GREEN" and record.available_for_downstream
               for record in records)
    assert not any(record.construction_status == "EXCEPTION" for record in records)

    # Proposed completion contract. This is orchestration state in the batch
    # graph, distinct from worker results and domain constraint knowledge.
    states = {
        state for state in batch.subjects(RDF.type, CV.ConstraintProductionState)
        if (state, CV.governedConstraint, constraint) in batch
    }
    assert len(states) == 1, (
        "IT-58R6S1 requires a persistent ConstraintProductionState for the "
        "completed row in the Batch Results Graph. Returning is_complete=True "
        "without a saved completion record is insufficient."
    )
    state = next(iter(states))
    assert isinstance(state, URIRef), "Production state must have a persistent RDF identity."
    assert set(batch.objects(state, CV.status)) == {Literal("COMPLETE")}
    assert set(batch.objects(state, CV.governedUniqueId)) == {Literal(unique_id)}
    assert set(batch.objects(state, CV.verifiedStageResult)) == {record.result_id for record in records}
    assert set(batch.objects(state, CV.rdfArtifact)) == {URIRef(rdf_path.resolve().as_uri())}
    assert set(batch.objects(state, CV.shaclArtifact)) == {URIRef(shacl_path.resolve().as_uri())}
    assert (state, PROV.wasDerivedFrom, source_iri) in batch
    for graph in (batch, rdf, shapes):
        assert not list(graph.subjects(RDF.type, SH.ValidationReport))
        assert not list(graph.subjects(RDF.type, SH.ValidationResult))
        assert not list(graph.subjects(RDF.type, CV.ReportFindingException))
    assert (source_path.read_bytes(), configuration_path.read_bytes()) == original_files
    assert [set(graph) for graph in model_inputs] == originals


