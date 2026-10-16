"""IT-51R4S2: exchange an exception instead of invented downstream knowledge."""

from __future__ import annotations

from uuid import uuid4

from rdflib import Graph, Literal, RDF, URIRef

from app.services.construction_exchange import (
    UADEX,
    exchange_construction_stage_exception,
)


def test_it_51_r4_s2_exchanges_exception_without_invented_downstream_knowledge() -> None:
    """An exception is preserved and withheld from downstream stages."""
    graph = Graph()
    constraint_id = f"urn:uad36:normalized-constraint:{uuid4().hex}"
    construction_stage = "logical-schema-binding"
    exception_reason = "The governed schema mapping is ambiguous."

    result = exchange_construction_stage_exception(
        exchange_graph=graph,
        constraint_id=constraint_id,
        construction_stage=construction_stage,
        exception_reason=exception_reason,
        requires_review=True,
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
        Literal("EXCEPTION"),
    ) in graph
    assert (
        result.result_id,
        UADEX.exceptionReason,
        Literal(exception_reason),
    ) in graph
    assert (
        result.result_id,
        UADEX.requiresReview,
        Literal(True),
    ) in graph
    assert (
        result.result_id,
        UADEX.availableForDownstream,
        Literal(False),
    ) in graph
    assert not any(graph.objects(result.result_id, UADEX.stageKnowledge))

    assert result.construction_status == "EXCEPTION"
    assert result.exception_reason == exception_reason
    assert result.requires_review is True
    assert result.available_for_downstream is False