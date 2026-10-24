"""IT-58R4S1: resume a reviewed row without repeating verified workers."""

from __future__ import annotations

import csv
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
def test_it_58_r4_s1_resumes_reviewed_row_without_repeating_verified_stages(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failed_index: int,
) -> None:
    pipeline = import_module("app.services.constraint_production_pipeline")
    resume = getattr(pipeline, "resume_governed_source_row", None)
    assert callable(resume), (
        "IT-58R4S1 requires resume_governed_source_row() to read a governed "
        "review resolution and persistent production state, restart the failed "
        "stage, and preserve previously verified stage identities without "
        "executing those workers again."
    )
    ns = Namespace(f"urn:uad36:test:it58r4s1:{uuid4().hex}:")
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
    inputs = (schema, projection, behaviors, patterns)
    inputs_before = [set(graph) for graph in inputs]
    output_directory = tmp_path / "production-artifacts"
    batch_path = tmp_path / "batch-state" / "results.ttl"
    arguments = dict(
        configuration_path=configuration_path,
        logical_schema_graph=schema,
        projection_model_graph=projection,
        established_behaviors_graph=behaviors,
        implementation_patterns_graph=patterns,
        output_directory=output_directory,
        batch_results_path=batch_path,
    )

    def no_evaluation(*args, **kwargs):
        pytest.fail("Resuming construction must not evaluate an appraisal or project findings.")

    monkeypatch.setattr(import_module("pyshacl"), "validate", no_evaluation)
    monkeypatch.setattr(
        import_module("app.services.validation_finding_projection"),
        "project_governed_findings", no_evaluation,
    )
    failed_stage = WORKERS[failed_index][2]
    failed_module = import_module(f"app.services.{WORKERS[failed_index][0]}")
    failed_operation = WORKERS[failed_index][1]
    input_name = WORKERS[failed_index][3]
    real_failed_worker = getattr(failed_module, failed_operation)
    reason = "Governed review is required before this worker can complete."

    def return_reviewable_exception(**kwargs):
        for triple in kwargs[input_name]:
            kwargs["output_graph"].add(triple)
        record = exchange_construction_stage_exception(
            exchange_graph=kwargs["output_graph"],
            constraint_id=kwargs["constraint_id"],
            construction_stage=failed_stage,
            exception_reason=reason,
            requires_review=True,
        )
        kwargs["output_graph"].add((record.result_id, PROV.wasDerivedFrom, source_iri))
        return record

    # First create genuine persisted exception/checkpoint state. The temporary
    # worker limitation is removed when the governed review below resolves it.
    with monkeypatch.context() as initial_patch:
        initial_patch.setattr(failed_module, failed_operation, return_reviewable_exception)
        if getattr(pipeline, failed_operation, None) is real_failed_worker:
            initial_patch.setattr(pipeline, failed_operation, return_reviewable_exception)
        initial = pipeline.process_all_governed_source_rows(**arguments)
    assert not initial.completed
    assert len(initial.exceptions) == 1
    failure = initial.exceptions[0]
    before = Graph().parse(batch_path, format="turtle")
    old_exception = read_construction_stage_result(
        exchange_graph=before, result_id=str(failure.result_id),
    )
    assert old_exception.construction_status == "EXCEPTION"
    assert old_exception.construction_stage == failed_stage
    constraint = URIRef(old_exception.constraint_id)
    stages = [worker[2] for worker in WORKERS]
    verified_ids = {}
    for stage in stages[:failed_index]:
        identities = {
            node for node in before.subjects(UADEX.forConstraint, constraint)
            if (node, UADEX.constructionStage, Literal(stage)) in before
        }
        assert len(identities) == 1
        record = read_construction_stage_result(
            exchange_graph=before, result_id=str(next(iter(identities))),
        )
        assert record.construction_status == "GREEN"
        assert record.available_for_downstream is True
        verified_ids[stage] = record.result_id
    verified_snapshots = {
        path: path.read_bytes()
        for path in output_directory.rglob("*.ttl")
        if "-unverified" not in path.name
        and any(path.name.startswith(f"{index + 1:02d}-") for index in range(failed_index))
    }
    assert len(verified_snapshots) == failed_index

    # Proposed review contract: an explicit resolution resource identifies the
    # exception, a RESOLVED decision, and the review activity and responsible
    # agent. Merely clearing requiresReview is not a governed resolution.
    for triple in (
        (ns.resolution, RDF.type, CV.GovernedReviewResolution),
        (ns.resolution, CV.resolvesException, failure.result_id),
        (ns.resolution, CV.reviewStatus, Literal("RESOLVED")),
        (ns.resolution, PROV.wasGeneratedBy, ns.review_activity),
        (ns.review_activity, RDF.type, PROV.Activity),
        (ns.review_activity, PROV.used, failure.result_id),
        (ns.review_activity, PROV.wasAssociatedWith, ns.reviewer),
        (ns.reviewer, RDF.type, PROV.Agent),
        (failure.result_id, CV.reviewResolution, ns.resolution),
    ):
        before.add(triple)
    before.serialize(destination=batch_path, format="turtle")
    resumed_calls = []

    def resume_observer(real, index, stage, input_key):
        def execute(*args, **kwargs):
            assert index >= failed_index, "Resume repeated an already verified production worker."
            assert index == failed_index + len(resumed_calls), "Resume started at the wrong stage or skipped a stage."
            incoming = kwargs[input_key]
            preceding_stage = stages[index - 1]
            candidates = {
                node for node in incoming.subjects(UADEX.forConstraint, constraint)
                if (node, UADEX.constructionStage, Literal(preceding_stage)) in incoming
                and (node, UADEX.constructionStatus, Literal("GREEN")) in incoming
                and (node, UADEX.availableForDownstream, Literal(True)) in incoming
            }
            assert len(candidates) == 1, "A resumed downstream worker consumed unverified input."
            if preceding_stage in verified_ids:
                assert candidates == {verified_ids[preceding_stage]}
            resumed_calls.append(stage)
            return real(*args, **kwargs)
        return execute

    for index, (module_name, operation_name, stage, input_key) in enumerate(WORKERS):
        module = import_module(f"app.services.{module_name}")
        real = getattr(module, operation_name)
        observed = resume_observer(real, index, stage, input_key)
        monkeypatch.setattr(module, operation_name, observed)
        if getattr(pipeline, operation_name, None) is real:
            monkeypatch.setattr(pipeline, operation_name, observed)

    result = resume(
        **arguments,
        unique_id=unique_id,
        review_resolution_id=str(ns.resolution),
    )
    assert resumed_calls == stages[failed_index:]
    assert result.is_complete is True
    assert result.constraint_id == str(constraint)
    assert result.unique_id == unique_id
    after = Graph().parse(batch_path, format="turtle")
    _assert_upstream_knowledge_preserved(before, after)
    for stage, result_id in verified_ids.items():
        records = {
            node for node in after.subjects(UADEX.forConstraint, constraint)
            if (node, UADEX.constructionStage, Literal(stage)) in after
        }
        assert records == {result_id}, "Resume replaced or duplicated a previously verified stage."
    for stage in stages:
        verified = {
            node for node in after.subjects(UADEX.forConstraint, constraint)
            if (node, UADEX.constructionStage, Literal(stage)) in after
            and (node, UADEX.constructionStatus, Literal("GREEN")) in after
            and (node, UADEX.availableForDownstream, Literal(True)) in after
        }
        assert len(verified) == 1, f"Resume did not persist one verified result for {stage}."
    preserved_exception = read_construction_stage_result(
        exchange_graph=after, result_id=str(failure.result_id),
    )
    assert preserved_exception.construction_status == "EXCEPTION"
    assert preserved_exception.exception_reason == reason
    for path, contents in verified_snapshots.items():
        assert path.read_bytes() == contents, "Resume rewrote a previously verified snapshot."
    rdf_path, shacl_path = Path(result.rdf_path), Path(result.shacl_path)
    for path in (rdf_path, shacl_path):
        assert path.is_file()
        assert path.resolve().is_relative_to(output_directory.resolve())
    rdf = Graph().parse(rdf_path, format="turtle")
    shapes = Graph().parse(shacl_path, format="turtle")
    assert (constraint, PROV.wasDerivedFrom, source_iri) in rdf
    assert set(rdf.objects(constraint, CV.governedUniqueId)) == {Literal(unique_id)}
    shape_ids = set(shapes.subjects(RDF.type, SH.NodeShape))
    assert len(shape_ids) == 1
    shape = next(iter(shape_ids))
    assert (shape, CV.implementsConstraint, constraint) in shapes
    assert (shape, PROV.wasDerivedFrom, source_iri) in shapes
    assert (source_path.read_bytes(), configuration_path.read_bytes()) == original_files
    assert [set(graph) for graph in inputs] == inputs_before


