"""IT-36R6S1 — record a GREEN normalization test result."""

from __future__ import annotations

from importlib import import_module

from rdflib import Graph, Literal, Namespace, RDF, URIRef
from rdflib.namespace import PROV


UADTEST = Namespace("https://dynamicontology.com/uad36/test/")
UADCV = Namespace("https://dynamicontology.com/uad36/constraint-vocabulary#")
UADCON = Namespace("https://dynamicontology.com/uad36/constraint/")


def _load_test_result_recorder():
    """Load the governed test-result behavior after RED exists."""
    try:
        module = import_module("app.services.normalization_test_result")
    except ModuleNotFoundError:
        return None

    return getattr(module, "record_normalization_test_result", None)


def test_it_36_r6_s1_records_green_normalization_test_result() -> None:
    """
    Feature: 1 Normalize governed constraints

    Rule: Record normalization test results as governed construction knowledge

    Scenario: Record a GREEN normalization test result
    """
    record_test_result = _load_test_result_recorder()

    assert record_test_result is not None, (
        "IT-36R6S1 requires "
        "app.services.normalization_test_result."
        "record_normalization_test_result"
    )

    graph = Graph()

    result = record_test_result(
        output_graph=graph,
        scenario_id="IT-36R5S2",
        status="GREEN",
        constraint_id="0100.0009",
        governed_source=(
            "specs/FannieMae/"
            "appendix-h-1-uad-compliance-rules-urar.xlsx"
        ),
    )

    test_result = URIRef(str(result.test_result_id))
    execution = URIRef(str(result.test_execution_id))
    constraint = URIRef(f"{UADCON}0100.0009")
    governed_source = URIRef(str(result.governed_source_id))

    assert (test_result, RDF.type, UADCV.TestResult) in graph
    assert (test_result, UADCV.scenarioId, Literal("IT-36R5S2")) in graph
    assert (test_result, UADCV.testStatus, Literal("GREEN")) in graph
    assert (test_result, UADCV.forConstraint, constraint) in graph

    assert (test_result, PROV.wasGeneratedBy, execution) in graph
    assert (execution, RDF.type, PROV.Activity) in graph

    assert (execution, PROV.used, governed_source) in graph
    assert (governed_source, RDF.type, PROV.Entity) in graph

    assert result.scenario_id == "IT-36R5S2"
    assert result.status == "GREEN"
    assert result.constraint_id == "0100.0009"
