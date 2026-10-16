"""IT-51R1S2: reuse a governed result identity across serializations."""

from __future__ import annotations

from uuid import uuid4

import pytest
from rdflib import Graph, URIRef

import app.services.construction_exchange as construction_exchange


@pytest.mark.parametrize("rdf_format", ["turtle", "xml"])
def test_it_51_r1_s2_reuses_result_identity_across_serializations(
    rdf_format: str,
) -> None:
    """Reloading an exchange graph recovers its existing result identity."""
    graph = Graph()
    constraint_id = f"urn:uad36:normalized-constraint:{uuid4().hex}"
    stage = "normalized-constraint-representation"
    status = "GREEN"

    original = construction_exchange.record_construction_stage_result(
        output_graph=graph,
        constraint_id=constraint_id,
        construction_stage=stage,
        construction_status=status,
    )

    serialized_graph = graph.serialize(format=rdf_format)
    reloaded_graph = Graph()
    reloaded_graph.parse(data=serialized_graph, format=rdf_format)

    read_result = getattr(
        construction_exchange,
        "read_construction_stage_result",
        None,
    )
    assert callable(read_result), (
        "The exchange service must read an existing stage result from a "
        "serialized graph instead of minting a new result identity."
    )

    restored = read_result(
        exchange_graph=reloaded_graph,
        result_id=str(original.result_id),
    )

    assert restored.result_id == original.result_id
    assert isinstance(restored.result_id, URIRef)
    assert restored.constraint_id == constraint_id
    assert restored.construction_stage == stage
    assert restored.construction_status == status