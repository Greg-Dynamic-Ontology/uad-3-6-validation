"""IT-51R3S2: preserve upstream knowledge when producing a downstream result."""

from __future__ import annotations

from uuid import uuid4

from rdflib import Graph, RDF, URIRef
from rdflib.namespace import PROV

from app.services.construction_exchange import (
    UADEX,
    record_construction_stage_result,
    record_downstream_stage_input,
    record_downstream_stage_result,
)


def test_it_51_r3_s2_preserves_upstream_knowledge_for_downstream_result() -> None:
    """The upstream result remains, and the downstream result is traceable to it."""
    graph = Graph()
    suffix = uuid4().hex
    constraint_id = f"urn:uad36:normalized-constraint:{suffix}"
    downstream_activity_id = f"urn:uad36:construction-activity:{suffix}"

    upstream = record_construction_stage_result(
        output_graph=graph,
        constraint_id=constraint_id,
        construction_stage="normalized-constraint-representation",
        construction_status="GREEN",
    )
    downstream_activity = URIRef(downstream_activity_id)

    record_downstream_stage_input(
        exchange_graph=graph,
        downstream_activity_id=downstream_activity_id,
        upstream_result_id=str(upstream.result_id),
    )
    downstream = record_downstream_stage_result(
        exchange_graph=graph,
        constraint_id=constraint_id,
        construction_stage="logical-schema-binding",
        construction_status="GREEN",
        downstream_activity_id=downstream_activity_id,
        upstream_result_id=str(upstream.result_id),
    )

    assert upstream.result_id != downstream.result_id
    assert (upstream.result_id, RDF.type, UADEX.ConstructionStageResult) in graph
    assert (downstream.result_id, RDF.type, UADEX.ConstructionStageResult) in graph
    assert (downstream_activity, PROV.used, upstream.result_id) in graph
    assert (
        downstream.result_id,
        PROV.wasGeneratedBy,
        downstream_activity,
    ) in graph
    assert (
        upstream.result_id,
        UADEX.forConstraint,
        URIRef(constraint_id),
    ) in graph
    assert (
        downstream.result_id,
        UADEX.forConstraint,
        URIRef(constraint_id),
    ) in graph