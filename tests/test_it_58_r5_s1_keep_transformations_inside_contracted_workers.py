"""IT-58R5S1: only contracted workers transform constraint knowledge."""

from __future__ import annotations

import csv
from importlib import import_module
from pathlib import Path
from uuid import uuid4

import pytest
from rdflib import Graph, Literal, Namespace, RDF, RDFS, URIRef
from rdflib.compare import isomorphic
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
from app.services.rdf_projection import UAD_SCHEMA


CV = Namespace("https://dynamicontology.com/uad36/constraint-vocabulary#")
CFG = Namespace("https://dynamicontology.com/uad36/configuration#")
LSM = Namespace("https://dynamicontology.com/uad36/logical-schema#")
WORKERS = (
    ("constraint_normalization_agent", "normalize_governed_constraint_to_file",
     "normalized-constraint-representation", None),
    ("logical_schema_binding_agent", "bind_normalized_constraint_to_logical_schema",
     "logical-schema-binding", "normalized_graph"),
    ("context_resolution_agent", "resolve_bound_constraint_context",
     "context-resolution", "bound_graph"),
    ("constraint_behavior_classification", "classify_governed_constraint_behavior",
     "validation-behavior", "context_graph"),
    ("instance_rdf_binding_agent", "bind_governed_constraint_to_instance_rdf",
     "instance-rdf-binding", "classified_graph"),
    ("shacl_generation_agent", "generate_governed_constraint_shacl",
     "shacl-representation", "bound_graph"),
)


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


def _domain_knowledge(graph: Graph) -> Graph:
    """Separate transformed domain knowledge from execution metadata.

    Include RDF list links so graph comparison checks path order and content
    while allowing serializers to rename blank nodes.
    """
    result = Graph()
    for subject, predicate, value in graph:
        if (
            str(predicate).startswith(str(CV))
            or str(predicate).startswith(str(SH))
            or predicate in (RDF.first, RDF.rest)
            or (predicate == RDF.type and (
                str(value).startswith(str(CV)) or str(value).startswith(str(SH))
            ))
        ):
            result.add((subject, predicate, value))
    return result


def test_it_58_r5_s1_keeps_knowledge_transformations_inside_contracted_workers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pipeline = import_module("app.services.constraint_production_pipeline")
    ns = Namespace(f"urn:uad36:test:it58r5s1:{uuid4().hex}:")
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
    calls = []
    published = []
    constraint_ids = []
    worker_shapes = []
    stage_predicates = (
        CV.dataPointName,
        CV.boundLogicalSchemaResource,
        CV.applicableContext,
        CV.behaviorClassification,
        CV.instanceRdfBinding,
        CV.shaclRepresentation,
    )

    def observe_worker(real, index, stage, input_name):
        def execute(*args, **kwargs):
            assert index == len(calls), "A contracted worker was skipped, repeated, or called out of order."
            if index == 0:
                assert kwargs["governed_source"]["unique_id"] == unique_id
                incoming_domain = Graph()
            else:
                constraint = URIRef(constraint_ids[0])
                incoming = kwargs[input_name]
                incoming_domain = _domain_knowledge(incoming)
                assert isomorphic(incoming_domain, published[-1]), (
                    "The pipeline changed domain knowledge between contracted workers."
                )
                preceding_results = {
                    result for result in incoming.subjects(UADEX.forConstraint, constraint)
                    if (result, UADEX.constructionStage, Literal(WORKERS[index - 1][2])) in incoming
                }
                assert len(preceding_results) == 1, "The governed RDF exchange handoff is missing."
                prior = read_construction_stage_result(
                    exchange_graph=incoming, result_id=str(next(iter(preceding_results))),
                )
                assert prior.construction_status == "GREEN"
                assert prior.available_for_downstream is True
                # A later transformation must not have been produced by an
                # earlier worker or filled in by the coordinator.
                for predicate in stage_predicates[index:]:
                    assert not list(incoming.objects(constraint, predicate)), (
                        "Domain knowledge was created before its owning worker executed."
                    )
            calls.append(stage)
            result = real(*args, **kwargs)
            if index == 0:
                constraint_ids.append(result.constraint_id)
                output = Graph().parse(kwargs["output_path"], format="turtle")
            else:
                output = kwargs["output_graph"]
            constraint = URIRef(constraint_ids[0])
            assert list(output.objects(constraint, stage_predicates[index])), (
                f"The contracted {stage} worker did not produce its domain transformation."
            )
            if index == 0:
                assert (constraint, RDF.type, CV.NormalizedConstraint) in output
                assert set(output.objects(constraint, CV.governedUniqueId)) == {Literal(unique_id)}
            output_domain = _domain_knowledge(output)
            # Capture RDF immediately as the real worker returns, before the
            # pipeline gets an opportunity to edit, supplement, or replace it.
            published.append(output_domain)
            if index == len(WORKERS) - 1:
                worker_shapes.append(Graph().parse(kwargs["output_path"], format="turtle"))
            return result
        return execute

    for index, (module_name, operation_name, stage, input_name) in enumerate(WORKERS):
        module = import_module(f"app.services.{module_name}")
        real = getattr(module, operation_name)
        observed = observe_worker(real, index, stage, input_name)
        monkeypatch.setattr(module, operation_name, observed)
        if getattr(pipeline, operation_name, None) is real:
            monkeypatch.setattr(pipeline, operation_name, observed)

    def no_evaluation(*args, **kwargs):
        pytest.fail("Production orchestration must not evaluate an appraisal or project runtime findings.")

    for module_name, operation_name in (
        ("pyshacl", "validate"),
        ("app.services.validation_finding_projection", "project_governed_findings"),
    ):
        module = import_module(module_name)
        real = getattr(module, operation_name)
        monkeypatch.setattr(module, operation_name, no_evaluation)
        if getattr(pipeline, operation_name, None) is real:
            monkeypatch.setattr(pipeline, operation_name, no_evaluation)

    batch_path = tmp_path / "batch-state" / "results.ttl"
    result = pipeline.process_governed_source_row(
        configuration_path=configuration_path,
        unique_id=unique_id,
        logical_schema_graph=schema,
        projection_model_graph=projection,
        established_behaviors_graph=behaviors,
        implementation_patterns_graph=patterns,
        output_directory=tmp_path / "production-artifacts",
        batch_results_path=batch_path,
    )
    assert calls == [worker[2] for worker in WORKERS]
    assert len(published) == len(WORKERS)
    assert result.is_complete is True
    assert result.constraint_id == constraint_ids[0]
    final_rdf = Graph().parse(result.rdf_path, format="turtle")
    final_shapes = Graph().parse(result.shacl_path, format="turtle")
    assert isomorphic(_domain_knowledge(final_rdf), published[-1]), (
        "The pipeline changed worker-produced domain knowledge in the completed artifact."
    )
    assert len(worker_shapes) == 1
    assert isomorphic(final_shapes, worker_shapes[0]), (
        "The pipeline replaced or supplemented the worker-generated SHACL artifact."
    )
    batch = Graph().parse(batch_path, format="turtle")
    records = [
        read_construction_stage_result(exchange_graph=batch, result_id=str(node))
        for node in batch.subjects(UADEX.forConstraint, URIRef(result.constraint_id))
    ]
    assert len(records) == len(WORKERS)
    assert {record.construction_stage for record in records} == set(calls)
    assert all(record.construction_status == "GREEN" and record.available_for_downstream
               for record in records)
    assert not list(batch.subjects(RDF.type, SH.ValidationResult))
    assert (source_path.read_bytes(), configuration_path.read_bytes()) == original_files
    assert [set(graph) for graph in model_inputs] == originals


