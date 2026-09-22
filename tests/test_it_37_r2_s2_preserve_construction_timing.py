"""IT-37R2S2 — preserve construction timing in the exchange graph."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from importlib import import_module

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import PROV, XSD


def _load_timing_recorder():
    """Load the governed exchange timing behavior after RED exists."""
    try:
        module = import_module("app.services.construction_exchange")
    except ModuleNotFoundError:
        return None

    return getattr(module, "record_construction_stage_timing", None)


def test_it_37_r2_s2_preserves_construction_timing_in_exchange_graph() -> None:
    """
    Feature: Define governed RDF exchange between constraint-construction stages

    Rule: Exchange knowledge preserves its construction provenance

    Scenario: Preserve construction timing in the exchange graph
    """
    record_stage_timing = _load_timing_recorder()

    assert record_stage_timing is not None, (
        "IT-37R2S2 requires "
        "app.services.construction_exchange."
        "record_construction_stage_timing"
    )

    graph = Graph()

    activity_id = URIRef(
        "https://dynamicontology.com/uad36/construction-exchange/"
        "activity/0100.0009-normalization"
    )

    started_at = datetime(2026, 9, 11, 13, 0, 0, tzinfo=timezone.utc)
    ended_at = started_at + timedelta(seconds=12)

    result = record_stage_timing(
        output_graph=graph,
        activity_id=str(activity_id),
        started_at=started_at,
        ended_at=ended_at,
    )

    assert result.activity_id == activity_id
    assert result.started_at == started_at
    assert result.ended_at == ended_at

    assert (
        activity_id,
        PROV.startedAtTime,
        Literal(started_at, datatype=XSD.dateTime),
    ) in graph
    assert (
        activity_id,
        PROV.endedAtTime,
        Literal(ended_at, datatype=XSD.dateTime),
    ) in graph
