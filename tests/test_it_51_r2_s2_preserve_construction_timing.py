"""IT-51R2S2: preserve construction timing in the exchange graph."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from rdflib import Graph, URIRef
from rdflib.namespace import PROV

from app.services.construction_exchange import (
    record_construction_stage_timing,
)


def test_it_51_r2_s2_preserves_construction_timing_in_exchange_graph() -> None:
    """The exchange graph records an activity's start and end times."""
    graph = Graph()
    activity_id = f"urn:uad36:construction-activity:{uuid4().hex}"
    activity = URIRef(activity_id)
    started_at = datetime(2026, 1, 15, 9, 30, tzinfo=timezone.utc)
    ended_at = datetime(2026, 1, 15, 9, 31, tzinfo=timezone.utc)

    timing = record_construction_stage_timing(
        output_graph=graph,
        activity_id=activity_id,
        started_at=started_at,
        ended_at=ended_at,
    )

    assert (activity, PROV.startedAtTime, None) in graph
    assert (activity, PROV.endedAtTime, None) in graph
    assert graph.value(activity, PROV.startedAtTime).toPython() == started_at
    assert graph.value(activity, PROV.endedAtTime).toPython() == ended_at
    assert timing.activity_id == activity
    assert timing.started_at == started_at
    assert timing.ended_at == ended_at