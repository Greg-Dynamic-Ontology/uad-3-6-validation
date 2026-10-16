"""IT-51R4S1: exchange a successful construction-stage result."""

from __future__ import annotations

from uuid import uuid4

from rdflib import Graph, Literal, RDF, URIRef

from app.services.construction_exchange import (
    UADEX,
    exchange_successful_construction_stage_result,
)


def test_it_51_r4_s1_exchanges_successful_construction_stage_result() -> None:
    """A successful result is GREEN and available to downstream stages."""
    graph = Graph()
    constraint_id = f"urn:uad36:normalized-constraint:{uuid4().hex}"
    construction_stage = "normalized-constraint-representation"

    result = exchange_successful_construction_stage_result(
        exchange_graph=graph,
        constraint_id=constraint_id,
        construction_stage=construction_stage,
    )

    assert (
        result.result_id,
        RDF.type,
        UADEX.ConstructionStageResult,
    ) in graph
    assert (
        result.result_id,
        UADEX.forConstraint,
        URIRef(constraint_id),
    ) in graph
    assert (
        result.result_id,
        UADEX.constructionStage,
        Literal(construction_stage),
    ) in graph
    assert (
        result.result_id,
        UADEX.constructionStatus,
        Literal("GREEN"),
    ) in graph
    assert (
        result.result_id,
        UADEX.availableForDownstream,
        Literal(True),
    ) in graph
    assert result.construction_status == "GREEN"
    assert result.available_for_downstream is True