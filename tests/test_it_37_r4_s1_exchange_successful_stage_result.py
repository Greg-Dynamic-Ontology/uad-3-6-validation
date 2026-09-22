"""IT-37R4S1 — exchange a successful construction-stage result."""

from __future__ import annotations

from importlib import import_module

from rdflib import Graph, Literal, Namespace, RDF, URIRef


UADEX = Namespace("https://dynamicontology.com/uad36/construction-exchange#")


def _load_successful_stage_exchange():
    """Load successful exchange behavior after RED exists."""
    try:
        module = import_module("app.services.construction_exchange")
    except ModuleNotFoundError:
        return None

    return getattr(module, "exchange_successful_construction_stage_result", None)


def test_it_37_r4_s1_exchanges_successful_construction_stage_result() -> None:
    """
    Feature: Define governed RDF exchange between constraint-construction stages

    Rule: Construction status and exceptions are exchange knowledge

    Scenario: Exchange a successful construction-stage result
    """
    exchange_success = _load_successful_stage_exchange()

    assert exchange_success is not None, (
        "IT-37R4S1 requires "
        "app.services.construction_exchange."
        "exchange_successful_construction_stage_result"
    )

    graph = Graph()

    result = exchange_success(
        exchange_graph=graph,
        constraint_id="0100.0009",
        construction_stage="normalized-constraint-representation",
    )

    result_id = URIRef(str(result.result_id))

    assert result.construction_status == "GREEN"
    assert result.available_for_downstream is True

    assert (
        result_id,
        RDF.type,
        UADEX.ConstructionStageResult,
    ) in graph
    assert (
        result_id,
        UADEX.constructionStatus,
        Literal("GREEN"),
    ) in graph
    assert (
        result_id,
        UADEX.availableForDownstream,
        Literal(True),
    ) in graph
