"""IT-36R6S3 — preserve warnings without converting them into failure."""

from __future__ import annotations

from importlib import import_module

from rdflib import Graph, Literal, Namespace, RDF, URIRef


UADCV = Namespace("https://dynamicontology.com/uad36/constraint-vocabulary#")


def _load_test_result_recorder():
    """Load the governed test-result behavior established by IT-36R6."""
    try:
        module = import_module("app.services.normalization_test_result")
    except ModuleNotFoundError:
        return None

    return getattr(module, "record_normalization_test_result", None)


def test_it_36_r6_s3_preserves_warnings_without_converting_them_to_failure() -> None:
    """
    Feature: 1 Normalize governed constraints

    Rule: Record normalization test results as governed construction knowledge

    Scenario: Preserve warnings without converting them into failure
    """
    record_test_result = _load_test_result_recorder()

    assert record_test_result is not None, (
        "IT-36R6S3 requires "
        "app.services.normalization_test_result."
        "record_normalization_test_result"
    )

    graph = Graph()
    warnings = [
        "Print area cannot be set to Defined name: "
        "'UAD Compliance Rules v1.5'!$A:$P.",
        "Print area cannot be set to Defined name: "
        "'UAD Compliance Rules(Marked up)'!$A:$P.",
        "Print area cannot be set to Defined name: "
        "'Column Description'!$A:$B.",
        "Print area cannot be set to Defined name: "
        "'Read Me'!$A:$B.",
        "Print area cannot be set to Defined name: "
        "'Tab Description'!$A:$B.",
    ]

    result = record_test_result(
        output_graph=graph,
        scenario_id="IT-36R5S2",
        status="GREEN",
        constraint_id="0100.0009",
        governed_source=(
            "specs/FannieMae/"
            "appendix-h-1-uad-compliance-rules-urar.xlsx"
        ),
        warnings=warnings,
    )

    test_result = URIRef(str(result.test_result_id))

    assert result.status == "GREEN"
    assert result.failure_reason is None
    assert result.warnings == tuple(warnings)

    assert (
        test_result,
        UADCV.testStatus,
        Literal("GREEN"),
    ) in graph

    recorded_warnings = {
        str(value)
        for value in graph.objects(test_result, UADCV.testWarning)
    }
    assert recorded_warnings == set(warnings)

    assert not list(graph.objects(test_result, UADCV.failureReason))
    assert (test_result, RDF.type, UADCV.TestResult) in graph
