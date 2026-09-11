"""IT-37R1S1 — represent a construction-stage result as governed RDF."""

from __future__ import annotations

from importlib import import_module

from rdflib import Graph, Literal, Namespace, RDF, URIRef


UADCON = Namespace("https://dynamicontology.com/uad36/constraint/")
UADEX = Namespace("https://dynamicontology.com/uad36/construction-exchange#")


def _load_exchange_result_recorder():
    """Load the governed exchange behavior after RED exists."""
    try:
        module = import_module("app.services.construction_exchange")
    except ModuleNotFoundError:
        return None

    return getattr(module, "record_construction_stage_result", None)


def test_it_37_r1_s1_represents_construction_stage_result_as_governed_rdf() -> None:
    """
    Feature: Define governed RDF exchange between constraint-construction stages

    Rule: A construction-stage result has an explicit governed identity

    Scenario: Represent a construction-stage result as governed RDF
    """
    record_stage_result = _load_exchange_result_recorder()

    assert record_stage_result is not None, (
        "IT-37R1S1 requires "
        "app.services.construction_exchange."
        "record_construction_stage_result"
    )

    graph = Graph()

    result = record_stage_result(
        output_graph=graph,
        constraint_id="0100.0009",
        construction_stage="normalized-constraint-representation",
        construction_status="GREEN",
    )

    result_id = URIRef(str(result.result_id))
    constraint_id = URIRef(f"{UADCON}0100.0009")

    assert isinstance(result_id, URIRef)
    assert str(result_id)

    assert (
        result_id,
        RDF.type,
        UADEX.ConstructionStageResult,
    ) in graph
    assert (
        result_id,
        UADEX.forConstraint,
        constraint_id,
    ) in graph
    assert (
        result_id,
        UADEX.constructionStage,
        Literal("normalized-constraint-representation"),
    ) in graph
    assert (
        result_id,
        UADEX.constructionStatus,
        Literal("GREEN"),
    ) in graph

    assert result.constraint_id == "0100.0009"
    assert result.construction_stage == "normalized-constraint-representation"
    assert result.construction_status == "GREEN"
