"""IT-51R3S1: consume a prior stage result through RDF identity."""

from __future__ import annotations

from uuid import uuid4

from rdflib import Graph, RDF, URIRef
from rdflib.namespace import PROV

from app.services.construction_exchange import (
    UADEX,
    record_construction_stage_result,
    record_downstream_stage_input,
)


def test_it_51_r3_s1_consumes_prior_stage_result_through_rdf_identity() -> None:
    """A downstream activity consumes the governed RDF result by its IRI."""
    graph = Graph()
    suffix = uuid4().hex
    constraint_id = f"urn:uad36:normalized-constraint:{suffix}"
    downstream_activity_id = f"urn:uad36:construction-activity:{suffix}"

    upstream_result = record_construction_stage_result(
        output_graph=graph,
        constraint_id=constraint_id,
        construction_stage="normalized-constraint-representation",
        construction_status="GREEN",
    )

    downstream_input = record_downstream_stage_input(
        exchange_graph=graph,
        downstream_activity_id=downstream_activity_id,
        upstream_result_id=str(upstream_result.result_id),
    )

    downstream_activity = URIRef(downstream_activity_id)

    assert (
        upstream_result.result_id,
        RDF.type,
        UADEX.ConstructionStageResult,
    ) in graph
    assert (downstream_activity, RDF.type, PROV.Activity) in graph
    assert (
        downstream_activity,
        PROV.used,
        upstream_result.result_id,
    ) in graph
    assert downstream_input.downstream_activity_id == downstream_activity
    assert downstream_input.upstream_result_id == upstream_result.result_id
    assert isinstance(downstream_input.upstream_result_id, URIRef)