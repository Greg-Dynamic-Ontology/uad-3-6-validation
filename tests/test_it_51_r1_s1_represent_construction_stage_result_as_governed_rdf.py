"""IT-51R1S1: represent a stage result with its governed RDF identity."""

from __future__ import annotations

from uuid import uuid4

from rdflib import Graph, Literal, RDF, URIRef

from app.services.construction_exchange import (
    UADEX,
    record_construction_stage_result,
)


def test_it_51_r1_s1_represents_construction_stage_result_as_governed_rdf() -> None:
    """The result identifies the exact governed constraint, stage, and status."""
    graph = Graph()
    governed_constraint_id = (
        f"urn:uad36:normalized-constraint:{uuid4().hex}"
    )
    governed_constraint = URIRef(governed_constraint_id)
    construction_stage = "normalized-constraint-representation"
    construction_status = "GREEN"

    result = record_construction_stage_result(
        output_graph=graph,
        constraint_id=governed_constraint_id,
        construction_stage=construction_stage,
        construction_status=construction_status,
    )

    assert isinstance(result.result_id, URIRef)
    assert (
        result.result_id,
        RDF.type,
        UADEX.ConstructionStageResult,
    ) in graph
    assert (
        result.result_id,
        UADEX.forConstraint,
        governed_constraint,
    ) in graph, (
        "The stage result must preserve the exact governed constraint IRI."
    )
    assert (
        result.result_id,
        UADEX.constructionStage,
        Literal(construction_stage),
    ) in graph
    assert (
        result.result_id,
        UADEX.constructionStatus,
        Literal(construction_status),
    ) in graph