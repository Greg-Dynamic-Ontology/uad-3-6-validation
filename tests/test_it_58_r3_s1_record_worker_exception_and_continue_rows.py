"""IT-58R3S1: preserve contracted worker exceptions and continue other rows."""

from __future__ import annotations

import csv
from collections import defaultdict
from importlib import import_module
from pathlib import Path
from uuid import uuid4

import pytest
from rdflib import BNode, Graph, Literal, Namespace, RDF, RDFS, URIRef
from rdflib.compare import isomorphic
from rdflib.namespace import OWL, PROV, SH, XSD

from app.models.schema_model import (
    ComplexTypeDefinition, ElementDeclaration, ModelGroup, ModelGroupKind,
    QName, SchemaModel,
)
from app.services.construction_exchange import (
    UADEX, exchange_construction_stage_exception, read_construction_stage_result,
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


def _assert_upstream_knowledge_preserved(expected: Graph, actual: Graph) -> None:
    """Check exact named terms and the structure of anchored blank nodes.

    Turtle parsers may rename blank nodes. They may not change governed IRIs,
    discard triples, reorder a list, or duplicate its branches. Compare all
    expected blank-node components together so shared nodes stay shared.
    """
    named_triples = {
        triple for triple in expected
        if not any(isinstance(term, BNode) for term in triple)
    }
    assert named_triples.issubset(set(actual)), (
        "Last verified upstream named knowledge was lost or changed."
    )
    roots = {
        (subject, predicate)
        for subject, predicate, value in expected
        if not isinstance(subject, BNode) and isinstance(value, BNode)
    }

    def components(graph: Graph) -> Graph:
        result = Graph()
        pending = []
        visited = set()
        for subject, predicate in roots:
            for value in graph.objects(subject, predicate):
                result.add((subject, predicate, value))
                if isinstance(value, BNode):
                    pending.append(value)
        while pending:
            node = pending.pop()
            if node in visited:
                continue
            visited.add(node)
            for triple in graph.triples((node, None, None)):
                result.add(triple)
                if isinstance(triple[2], BNode):
                    pending.append(triple[2])
        return result

    expected_components = components(expected)
    # Ensure the helper itself does not overlook unanchored blank-node facts.
    assert all(
        triple in expected_components for triple in expected
        if any(isinstance(term, BNode) for term in triple)
    ), "The test fixture contains an unanchored blank-node component."
    assert isomorphic(expected_components, components(actual)), (
        "Last verified upstream blank-node structure changed: RDF lists or "
        "other blank-node knowledge were lost, altered, or duplicated."
    )


@pytest.mark.parametrize("failed_index", range(1, 6), ids=[
    "logical-schema-binding", "context-resolution", "validation-behavior",
    "instance-rdf-binding", "shacl-generation",
])
def test_it_58_r3_s1_records_contracted_worker_exception_and_continues_rows(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failed_index: int,
) -> None:
    pipeline = import_module("app.services.constraint_production_pipeline")
    ns = Namespace(f"urn:uad36:test:it58r3s1:{uuid4().hex}:")
    before_id, failed_id, after_id = ("0" + uuid4().hex for _ in range(3))
    row_ids = (before_id, failed_id, after_id)
    requirement = "Provide the address line for each property."
    violation = "The property address line is absent."
    rows = []
    for unique_id in row_ids:
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
        rows.append(row)
    source_path = tmp_path / "constraints.csv"
    with source_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=EXPECTED_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    failed_source = URIRef(f"urn:uad36:governed-source:{source_path.name}#row=3")
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
    source_before = source_path.read_bytes()
    configuration_before = configuration_path.read_bytes()

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
    inputs = (schema, projection, behaviors, patterns)
    inputs_before = [set(graph) for graph in inputs]
    calls = defaultdict(list)
    events = []
    contracted_results = []
    upstream_snapshot = Graph()
    last_verified_ids = []
    reason = "Contracted worker cannot complete governed stage " + WORKERS[failed_index][2]

    def observe_worker(real, index, stage, input_name):
        def execute(*args, **kwargs):
            preceding = None
            if input_name is None:
                unique_id = kwargs["governed_source"]["unique_id"]
                incoming = None
            else:
                incoming = kwargs[input_name]
                identities = set(incoming.objects(URIRef(kwargs["constraint_id"]), CV.governedUniqueId))
                assert len(identities) == 1
                unique_id = str(next(iter(identities)))
                preceding_ids = set(incoming.subjects(
                    UADEX.constructionStage, Literal(WORKERS[index - 1][2]),
                ))
                assert len(preceding_ids) == 1
                preceding = read_construction_stage_result(
                    exchange_graph=incoming, result_id=str(next(iter(preceding_ids))),
                )
                assert preceding.construction_status == "GREEN"
                assert preceding.available_for_downstream is True
            assert unique_id in row_ids
            assert index == len(calls[unique_id]), "A worker was skipped, repeated, or run out of order."
            if unique_id == failed_id:
                assert index <= failed_index, "Downstream production executed after a contracted exception."
            calls[unique_id].append(stage)
            events.append((unique_id, stage))
            if unique_id == failed_id and index == failed_index:
                assert incoming is not None
                assert preceding is not None
                for triple in incoming:
                    upstream_snapshot.add(triple)
                    kwargs["output_graph"].add(triple)
                last_verified_ids.append(preceding.result_id)
                result = exchange_construction_stage_exception(
                    exchange_graph=kwargs["output_graph"],
                    constraint_id=kwargs["constraint_id"],
                    construction_stage=stage,
                    exception_reason=reason,
                    requires_review=True,
                )
                kwargs["output_graph"].add((result.result_id, PROV.wasDerivedFrom, failed_source))
                contracted_results.append(result)
                return result
            return real(*args, **kwargs)
        return execute

    # Keep real workers on both successful rows and on every stage before
    # the selected failure. Only the chosen worker/row returns a test exception.
    for index, (module_name, operation_name, stage, input_name) in enumerate(WORKERS):
        module = import_module(f"app.services.{module_name}")
        real = getattr(module, operation_name)
        observed = observe_worker(real, index, stage, input_name)
        monkeypatch.setattr(module, operation_name, observed)
        if getattr(pipeline, operation_name, None) is real:
            monkeypatch.setattr(pipeline, operation_name, observed)

    def no_evaluation(*args, **kwargs):
        pytest.fail("Constraint construction must not evaluate appraisal XML or produce findings.")

    monkeypatch.setattr(import_module("pyshacl"), "validate", no_evaluation)
    monkeypatch.setattr(
        import_module("app.services.validation_finding_projection"),
        "project_governed_findings", no_evaluation,
    )
    batch_path = tmp_path / "batch-state" / "results.ttl"
    output_directory = tmp_path / "production-artifacts"
    result = pipeline.process_all_governed_source_rows(
        configuration_path=configuration_path,
        logical_schema_graph=schema,
        projection_model_graph=projection,
        established_behaviors_graph=behaviors,
        implementation_patterns_graph=patterns,
        output_directory=output_directory,
        batch_results_path=batch_path,
    )

    stages = [worker[2] for worker in WORKERS]
    assert calls[failed_id] == stages[:failed_index + 1]
    assert calls[before_id] == stages
    assert calls[after_id] == stages
    assert events.index((after_id, stages[0])) > events.index((failed_id, stages[failed_index]))
    completed = list(result.completed)
    exceptions = list(result.exceptions)
    assert len(completed) == 2
    assert {item.unique_id for item in completed} == {before_id, after_id}
    assert len(exceptions) == 1
    assert len(contracted_results) == 1
    original = contracted_results[0]
    failure = exceptions[0]
    assert failure.unique_id == failed_id
    assert failure.result_id == original.result_id, "The worker exception identity was replaced."
    assert failure.construction_stage == stages[failed_index]
    assert failure.exception_reason == reason
    assert failure.source_constraint_uri == str(failed_source)

    batch = Graph().parse(batch_path, format="turtle")
    _assert_upstream_knowledge_preserved(upstream_snapshot, batch)
    saved = read_construction_stage_result(exchange_graph=batch, result_id=str(original.result_id))
    assert saved.construction_status == "EXCEPTION"
    assert saved.construction_stage == stages[failed_index]
    assert saved.exception_reason == reason
    assert saved.available_for_downstream is False
    assert saved.requires_review is True
    assert (original.result_id, CV.governedUniqueId, Literal(failed_id)) in batch
    assert (original.result_id, PROV.wasDerivedFrom, failed_source) in batch
    prior = read_construction_stage_result(exchange_graph=batch, result_id=str(last_verified_ids[0]))
    assert prior.construction_stage == stages[failed_index - 1]
    assert prior.construction_status == "GREEN"
    assert prior.available_for_downstream is True
    failed_constraint = URIRef(original.constraint_id)
    failed_results = [
        read_construction_stage_result(exchange_graph=batch, result_id=str(node))
        for node in batch.subjects(UADEX.forConstraint, failed_constraint)
    ]
    assert len(failed_results) == failed_index + 1
    assert {record.construction_stage for record in failed_results} == set(stages[:failed_index + 1])
    assert sum(record.construction_status == "EXCEPTION" for record in failed_results) == 1
    assert not list(batch.objects(failed_constraint, CV.shaclRepresentation))

    for item in completed:
        assert item.is_complete is True
        rdf = Graph().parse(item.rdf_path, format="turtle")
        shapes = Graph().parse(item.shacl_path, format="turtle")
        assert set(rdf.objects(URIRef(item.constraint_id), CV.governedUniqueId)) == {Literal(item.unique_id)}
        assert (failed_constraint, RDF.type, CV.NormalizedConstraint) not in rdf
        assert list(shapes.subjects(CV.implementsConstraint, URIRef(item.constraint_id)))
    # The failed row must not leave completed artifacts alongside the good rows.
    assert len(list(output_directory.rglob("constraint.ttl"))) == 2
    assert len(list(output_directory.rglob("shapes.ttl"))) == 2
    assert not list(batch.subjects(RDF.type, SH.ValidationResult))
    assert source_path.read_bytes() == source_before
    assert configuration_path.read_bytes() == configuration_before
    assert [set(graph) for graph in inputs] == inputs_before


