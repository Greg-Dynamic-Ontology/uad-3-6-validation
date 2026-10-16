"""IT-51R2S1: link a stage result to its generating activity."""

from __future__ import annotations

from uuid import uuid4

from rdflib import Graph, RDF, URIRef
from rdflib.namespace import PROV

from app.services.construction_exchange import (
    UADEX,
    record_construction_stage_provenance,
    record_construction_stage_result,
)


def test_it_51_r2_s1_links_stage_result_to_generating_activity() -> None:
    """The result, responsible worker, and used knowledge remain traceable."""
    graph = Graph()
    suffix = uuid4().hex
    constraint_id = f"urn:uad36:normalized-constraint:{suffix}"
    activity_id = f"urn:uad36:construction-activity:{suffix}"
    worker_id = f"urn:uad36:construction-worker:{suffix}"
    source_knowledge_id = f"urn:uad36:construction-knowledge:{suffix}"

    result = record_construction_stage_result(
        output_graph=graph,
        constraint_id=constraint_id,
        construction_stage="normalized-constraint-representation",
        construction_status="GREEN",
    )

    provenance = record_construction_stage_provenance(
        output_graph=graph,
        result_id=str(result.result_id),
        activity_id=activity_id,
        agent_id=worker_id,
        used_knowledge_ids=[source_knowledge_id],
    )

    activity = URIRef(activity_id)
    worker = URIRef(worker_id)
    source_knowledge = URIRef(source_knowledge_id)

    assert (result.result_id, RDF.type, UADEX.ConstructionStageResult) in graph
    assert (result.result_id, PROV.wasGeneratedBy, activity) in graph
    assert (activity, RDF.type, PROV.Activity) in graph
    assert (activity, PROV.wasAssociatedWith, worker) in graph
    assert (worker, RDF.type, PROV.Agent) in graph
    assert (activity, PROV.used, source_knowledge) in graph
    assert (source_knowledge, RDF.type, PROV.Entity) in graph

    assert provenance.result_id == result.result_id
    assert provenance.activity_id == activity
    assert provenance.agent_id == worker
    assert provenance.used_knowledge_ids == (source_knowledge,)