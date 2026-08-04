"""Ontology tests for pipeline execution and failure reporting."""

from pathlib import Path

from rdflib import Graph, Namespace
from rdflib.namespace import OWL, RDF, RDFS, XSD

from app.core.namespaces import UAD


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CORE_ONTOLOGY_FILE = PROJECT_ROOT / "ontologies" / "uad36-core.ttl"
PROV = Namespace("http://www.w3.org/ns/prov#")


def load_core_ontology() -> Graph:
    graph = Graph()
    graph.parse(CORE_ONTOLOGY_FILE, format="turtle")
    return graph


def test_pipeline_execution_classes_are_declared() -> None:
    graph = load_core_ontology()

    expected_classes = {
        UAD.PipelineRun,
        UAD.StageExecution,
        UAD.RdfProjectionExecution,
        UAD.PipelineError,
        UAD.ExecutionStatus,
    }

    for expected_class in expected_classes:
        assert (expected_class, RDF.type, OWL.Class) in graph

    assert (
        UAD.RdfProjectionExecution,
        RDFS.subClassOf,
        UAD.StageExecution,
    ) in graph


def test_pipeline_execution_uses_prov_activity_semantics() -> None:
    graph = load_core_ontology()

    assert (
        UAD.PipelineRun,
        RDFS.subClassOf,
        PROV.Activity,
    ) in graph
    assert (
        UAD.StageExecution,
        RDFS.subClassOf,
        PROV.Activity,
    ) in graph


def test_pipeline_execution_relationships_are_declared() -> None:
    graph = load_core_ontology()

    assert (UAD.hasStageExecution, RDF.type, OWL.ObjectProperty) in graph
    assert (UAD.hasError, RDF.type, OWL.ObjectProperty) in graph
    assert (UAD.executionStatus, RDF.type, OWL.ObjectProperty) in graph

    assert (UAD.hasStageExecution, RDFS.domain, UAD.PipelineRun) in graph
    assert (UAD.hasStageExecution, RDFS.range, UAD.StageExecution) in graph
    assert (UAD.hasError, RDFS.domain, UAD.StageExecution) in graph
    assert (UAD.hasError, RDFS.range, UAD.PipelineError) in graph
    assert (UAD.executionStatus, RDFS.range, UAD.ExecutionStatus) in graph


def test_pipeline_error_carries_business_and_technical_messages() -> None:
    graph = load_core_ontology()

    for message_property in (
        UAD.errorCode,
        UAD.businessMessage,
        UAD.technicalMessage,
    ):
        assert (message_property, RDF.type, OWL.DatatypeProperty) in graph
        assert (message_property, RDFS.domain, UAD.PipelineError) in graph
        assert (message_property, RDFS.range, XSD.string) in graph


def test_pipeline_execution_status_individuals_are_declared() -> None:
    graph = load_core_ontology()

    assert (UAD.Completed, RDF.type, UAD.ExecutionStatus) in graph
    assert (UAD.Failed, RDF.type, UAD.ExecutionStatus) in graph
