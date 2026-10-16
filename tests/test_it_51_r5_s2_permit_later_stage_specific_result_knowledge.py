"""IT-51R5S2: permit later stages to define their own result knowledge."""

from __future__ import annotations

from uuid import uuid4

from rdflib import Graph, Literal, Namespace, RDF, URIRef

from app.services.construction_exchange import (
    UADEX,
    carry_stage_specific_knowledge,
    record_construction_stage_result,
)


def test_it_51_r5_s2_preserves_later_stage_specific_rdf_knowledge() -> None:
    """Later-stage knowledge keeps its own RDF type and predicates."""
    graph = Graph()
    suffix = uuid4().hex
    later_vocabulary = Namespace(f"urn:uad36:later-stage-vocabulary:{suffix}#")
    constraint_id = f"urn:uad36:normalized-constraint:{suffix}"
    later_knowledge_id = URIRef(f"urn:uad36:logical-schema-binding:{suffix}")
    stage_name = "logical-schema-binding"
    governed_mapping = f"mapping-{suffix}"

    graph.add((later_knowledge_id, RDF.type, later_vocabulary.SchemaBinding))
    graph.add(
        (
            later_knowledge_id,
            later_vocabulary.governedMapping,
            Literal(governed_mapping),
        )
    )

    result = record_construction_stage_result(
        output_graph=graph,
        constraint_id=constraint_id,
        construction_stage=stage_name,
        construction_status="GREEN",
    )

    carried = carry_stage_specific_knowledge(
        exchange_graph=graph,
        result_id=str(result.result_id),
        stage_knowledge_id=str(later_knowledge_id),
        expected_stage=stage_name,
        expected_knowledge_type=str(later_vocabulary.SchemaBinding),
    )

    assert (result.result_id, RDF.type, UADEX.ConstructionStageResult) in graph
    assert (
        result.result_id,
        UADEX.constructionStage,
        Literal(stage_name),
    ) in graph
    assert (
        result.result_id,
        UADEX.stageKnowledge,
        later_knowledge_id,
    ) in graph
    assert (
        later_knowledge_id,
        RDF.type,
        later_vocabulary.SchemaBinding,
    ) in graph
    assert (
        later_knowledge_id,
        later_vocabulary.governedMapping,
        Literal(governed_mapping),
    ) in graph
    assert not any(
        graph.objects(later_knowledge_id, UADEX.genericKnowledgeText)
    )
    assert carried.result_id == result.result_id
    assert carried.stage_knowledge_id == later_knowledge_id