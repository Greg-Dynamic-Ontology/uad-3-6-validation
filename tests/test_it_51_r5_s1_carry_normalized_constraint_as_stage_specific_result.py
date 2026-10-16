"""IT-51R5S1: carry normalized constraint knowledge as a stage result."""

from __future__ import annotations

from uuid import uuid4

from rdflib import Graph, Literal, RDF, URIRef

from app.services.construction_exchange import (
    UADEX,
    carry_stage_specific_knowledge,
    record_construction_stage_result,
)
from app.services.constraint_normalization_agent import (
    NORMALIZATION_STAGE,
    UADCV,
)


def test_it_51_r5_s1_carries_normalized_constraint_as_stage_specific_result() -> None:
    """The exchange result links to normalized RDF without replacing it."""
    graph = Graph()
    suffix = uuid4().hex
    normalized_constraint = URIRef(
        f"urn:uad36:normalized-constraint:{suffix}"
    )
    unique_id = f"test-{suffix}"
    data_point_name = f"TestDataPoint-{suffix}"
    stage_result = record_construction_stage_result(
        output_graph=graph,
        constraint_id=str(normalized_constraint),
        construction_stage=NORMALIZATION_STAGE,
        construction_status="GREEN",
    )

    graph.add((normalized_constraint, RDF.type, UADCV.NormalizedConstraint))
    graph.add(
        (normalized_constraint, UADCV.governedUniqueId, Literal(unique_id))
    )
    graph.add(
        (
            normalized_constraint,
            UADCV.dataPointName,
            Literal(data_point_name),
        )
    )

    carried = carry_stage_specific_knowledge(
        exchange_graph=graph,
        result_id=str(stage_result.result_id),
        stage_knowledge_id=str(normalized_constraint),
        expected_stage=NORMALIZATION_STAGE,
        expected_knowledge_type=str(UADCV.NormalizedConstraint),
    )

    assert (
        stage_result.result_id,
        UADEX.stageKnowledge,
        normalized_constraint,
    ) in graph
    assert (
        stage_result.result_id,
        UADEX.constructionStage,
        Literal(NORMALIZATION_STAGE),
    ) in graph
    assert (
        normalized_constraint,
        RDF.type,
        UADCV.NormalizedConstraint,
    ) in graph
    assert (
        normalized_constraint,
        UADCV.governedUniqueId,
        Literal(unique_id),
    ) in graph
    assert (
        normalized_constraint,
        UADCV.dataPointName,
        Literal(data_point_name),
    ) in graph
    assert carried.result_id == stage_result.result_id
    assert carried.stage_knowledge_id == normalized_constraint