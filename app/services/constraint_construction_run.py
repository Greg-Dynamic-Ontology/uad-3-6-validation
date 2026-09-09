"""Create and record governed constraint-construction run knowledge."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4


BASE_RUN_IRI = "https://dynamicontology.com/uad36/construction/run/"


@dataclass(frozen=True)
class ConstraintConstructionRunRecord:
    """Governed identity record for one construction run activity and result."""

    run_id: str
    activity_id: str
    result_id: str
    batch_id: str
    constraint_id: str
    construction_stage: str
    agent_id: str
    used_knowledge: list[str]
    generated_by_activity: str
    result_for_constraint: str
    stage_status: str
    identity_strategy: str


@dataclass(frozen=True)
class ConstructionActivityTimingRecord:
    """Temporal and causal knowledge for one construction activity."""

    activity_id: str
    started_at: datetime
    ended_at: datetime
    generated_result_id: str
    result_generated_by: str
    parent_activity_id: str | None


def create_constraint_construction_run(
    *,
    batch_id: str,
    constraint_id: str,
    construction_stage: str,
    agent_id: str,
    used_knowledge: list[str],
    stage_status: str,
) -> ConstraintConstructionRunRecord:
    """
    Create governed run, activity, and result identities independent of write order.

    UUID-based execution identities are used so concurrent activities do not depend
    on serialization order or disk-write order.
    """
    run_token = uuid4().hex
    activity_token = uuid4().hex
    result_token = uuid4().hex

    run_id = f"{BASE_RUN_IRI}{run_token}"
    activity_id = f"{run_id}/activity/{activity_token}"
    result_id = f"{run_id}/result/{result_token}"

    return ConstraintConstructionRunRecord(
        run_id=run_id,
        activity_id=activity_id,
        result_id=result_id,
        batch_id=batch_id,
        constraint_id=constraint_id,
        construction_stage=construction_stage,
        agent_id=agent_id,
        used_knowledge=list(used_knowledge),
        generated_by_activity=activity_id,
        result_for_constraint=constraint_id,
        stage_status=stage_status,
        identity_strategy="run-activity-result",
    )


def record_construction_activity_timing(
    *,
    activity_id: str,
    started_at: datetime,
    ended_at: datetime,
    generated_result_id: str,
) -> ConstructionActivityTimingRecord:
    """
    Record temporal and causal facts for one construction activity.

    The record carries its own timestamps so execution order can be reconstructed
    independently of serialization or disk-write order. No parent-child activity
    relationship is imposed.
    """
    if ended_at < started_at:
        raise ValueError("ended_at cannot be earlier than started_at")

    return ConstructionActivityTimingRecord(
        activity_id=activity_id,
        started_at=started_at,
        ended_at=ended_at,
        generated_result_id=generated_result_id,
        result_generated_by=activity_id,
        parent_activity_id=None,
    )


@dataclass(frozen=True)
class SharedConstructionKnowledgeRelationship:
    """Graph relationship between one governed result and its consumers."""

    knowledge_id: str
    consuming_activity_ids: list[str]
    knowledge_instance_count: int
    parent_activity_id: str | None
    topology: str


def link_shared_construction_knowledge(
    *,
    knowledge_id: str,
    consuming_activity_ids: list[str],
) -> SharedConstructionKnowledgeRelationship:
    """
    Link one governed knowledge result to every activity that consumes it.

    The knowledge retains one identity regardless of how many activities use it.
    No artificial parent-child relationship is introduced merely to force the
    execution topology into a tree.
    """
    return SharedConstructionKnowledgeRelationship(
        knowledge_id=knowledge_id,
        consuming_activity_ids=list(consuming_activity_ids),
        knowledge_instance_count=1,
        parent_activity_id=None,
        topology="directed-graph",
    )


__all__ = [
    "ConstraintConstructionRunRecord",
    "ConstructionActivityTimingRecord",
    "SharedConstructionKnowledgeRelationship",
    "create_constraint_construction_run",
    "record_construction_activity_timing",
    "link_shared_construction_knowledge",
]
