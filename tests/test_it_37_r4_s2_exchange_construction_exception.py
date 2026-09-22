"""IT-37R4S2 — exchange an exception instead of invented downstream knowledge."""

from __future__ import annotations

from importlib import import_module

from rdflib import Graph, Literal, Namespace, RDF, URIRef


UADEX = Namespace("https://dynamicontology.com/uad36/construction-exchange#")


def _load_exception_exchange():
    """Load construction-stage exception exchange behavior after RED exists."""
    try:
        module = import_module("app.services.construction_exchange")
    except ModuleNotFoundError:
        return None

    return getattr(module, "exchange_construction_stage_exception", None)


def test_it_37_r4_s2_exchanges_exception_without_inventing_successful_output() -> None:
    """
    Feature: Define governed RDF exchange between constraint-construction stages

    Rule: Construction status and exceptions are exchange knowledge

    Scenario: Exchange an exception instead of invented downstream knowledge
    """
    exchange_exception = _load_exception_exchange()

    assert exchange_exception is not None, (
        "IT-37R4S2 requires "
        "app.services.construction_exchange."
        "exchange_construction_stage_exception"
    )

    graph = Graph()

    result = exchange_exception(
        exchange_graph=graph,
        constraint_id="0100.0009",
        construction_stage="logical-schema-binding",
        exception_reason=(
            "The available governed knowledge is insufficient "
            "to select one logical-schema binding."
        ),
        requires_review=True,
    )

    result_id = URIRef(str(result.result_id))

    assert result.construction_status == "EXCEPTION"
    assert result.exception_reason == (
        "The available governed knowledge is insufficient "
        "to select one logical-schema binding."
    )
    assert result.requires_review is True
    assert result.available_for_downstream is False

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
        UADEX.exceptionReason,
        Literal(result.exception_reason),
    ) in graph
    assert (
        result_id,
        UADEX.requiresReview,
        Literal(True),
    ) in graph
    assert (
        result_id,
        UADEX.availableForDownstream,
        Literal(False),
    ) in graph

    # An exception is governed construction knowledge, not a successful
    # stage output made up merely to let the pipeline continue.
    successful_results = {
        subject
        for subject in graph.subjects(
            UADEX.constructionStatus,
            Literal("GREEN"),
        )
    }
    assert successful_results == set()
