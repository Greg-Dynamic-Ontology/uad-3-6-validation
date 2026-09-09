"""IT-34R2S1 — record activity timing independently of graph write order."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from importlib import import_module


def _load_timing_recorder():
    """Load the production timing behavior after the RED test exists."""
    try:
        module = import_module("app.services.constraint_construction_run")
    except ModuleNotFoundError:
        return None
    return getattr(module, "record_construction_activity_timing", None)


def test_it_34_r2_s1_records_activity_timing_independently_of_write_order() -> None:
    """Record temporal and causal facts without relying on graph write order."""
    record_construction_activity_timing = _load_timing_recorder()

    assert record_construction_activity_timing is not None, (
        "IT-34R2S1 requires "
        "app.services.constraint_construction_run."
        "record_construction_activity_timing"
    )

    base = datetime(2026, 9, 9, 16, 0, 0, tzinfo=timezone.utc)

    activity_a = record_construction_activity_timing(
        activity_id="https://dynamicontology.com/uad36/construction/run/run-1/activity/activity-a",
        started_at=base,
        ended_at=base + timedelta(seconds=20),
        generated_result_id="https://dynamicontology.com/uad36/construction/run/run-1/result/result-a",
    )
    activity_b = record_construction_activity_timing(
        activity_id="https://dynamicontology.com/uad36/construction/run/run-1/activity/activity-b",
        started_at=base + timedelta(seconds=5),
        ended_at=base + timedelta(seconds=10),
        generated_result_id="https://dynamicontology.com/uad36/construction/run/run-1/result/result-b",
    )

    assert activity_a.started_at == base
    assert activity_b.started_at == base + timedelta(seconds=5)
    assert activity_a.ended_at == base + timedelta(seconds=20)
    assert activity_b.ended_at == base + timedelta(seconds=10)

    assert activity_a.result_generated_by == activity_a.activity_id
    assert activity_b.result_generated_by == activity_b.activity_id

    chronological_by_start = sorted(
        [activity_b, activity_a], key=lambda activity: activity.started_at
    )
    assert [activity.activity_id for activity in chronological_by_start] == [
        activity_a.activity_id,
        activity_b.activity_id,
    ]

    chronological_by_completion = sorted(
        [activity_a, activity_b], key=lambda activity: activity.ended_at
    )
    assert [activity.activity_id for activity in chronological_by_completion] == [
        activity_b.activity_id,
        activity_a.activity_id,
    ]

    assert activity_a.parent_activity_id is None
    assert activity_b.parent_activity_id is None
