"""IT-37R6S1 — keep construction failure distinct from appraisal validation failure."""

from __future__ import annotations

from importlib import import_module

from rdflib import Graph, Literal, Namespace, RDF, URIRef


UADEX = Namespace("https://dynamicontology.com/uad36/construction-exchange#")
SH = Namespace("http://www.w3.org/ns/shacl#")


def _load_boundary_behavior():
    """Load construction/validation boundary behavior after RED exists."""
    try:
        module = import_module("app.services.construction_exchange")
    except ModuleNotFoundError:
        return None

    return getattr(module, "record_construction_failure", None)


def test_it_37_r6_s1_keeps_construction_failure_distinct_from_appraisal_validation_failure() -> None:
    """
    Feature: Define governed RDF exchange between constraint-construction stages

    Rule: The exchange graph preserves the constraint-construction and
          validation-execution boundary

    Scenario: Keep construction failure distinct from appraisal validation failure
    """
    record_construction_failure = _load_boundary_behavior()

    assert record_construction_failure is not None, (
        "IT-37R6S1 requires "
        "app.services.construction_exchange.record_construction_failure"
    )

    graph = Graph()

    result_id = URIRef(
        "https://dynamicontology.com/uad36/construction-exchange/"
        "result/0100.0009-logical-schema-binding"
    )

    result = record_construction_failure(
        exchange_graph=graph,
        result_id=str(result_id),
        constraint_id="0100.0009",
        construction_stage="logical-schema-binding",
        failure_reason="No governed Logical Schema binding was established.",
    )

    assert result.result_id == result_id
    assert result.construction_status == "EXCEPTION"

    assert (
        result_id,
        RDF.type,
        UADEX.ConstructionStageResult,
    ) in graph
    assert (
        result_id,
        UADEX.constructionStatus,
        Literal("EXCEPTION"),
    ) in graph
    assert (
        result_id,
        UADEX.failureReason,
        Literal("No governed Logical Schema binding was established."),
    ) in graph

    # A construction failure is knowledge about the constraint-production
    # process. It must not become an appraisal-validation result.
    assert (
        result_id,
        RDF.type,
        SH.ValidationResult,
    ) not in graph
    assert (
        result_id,
        RDF.type,
        SH.ValidationReport,
    ) not in graph

    # Nor may the exchange graph invent SHACL validation-result knowledge
    # merely because construction failed.
    assert not list(graph.subjects(RDF.type, SH.ValidationResult))
    assert not list(graph.subjects(RDF.type, SH.ValidationReport))
