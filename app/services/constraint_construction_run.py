"""Create and record governed constraint-construction run knowledge."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from rdflib import Namespace, RDF, URIRef


BASE_RUN_IRI = "https://dynamicontology.com/uad36/construction/run/"
PROV = Namespace("http://www.w3.org/ns/prov#")


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


CONSTRUCTION_STAGES = frozenset(
    {
        "normalized-constraint-representation",
        "logical-schema-binding",
        "context-resolution",
        "validation-behavior",
        "instance-rdf-binding",
        "shacl-representation",
        "finding-definition",
    }
)

VALIDATION_EXECUTION_STAGES = frozenset(
    {
        "received-file-validation",
        "shacl-validation-result",
        "governed-validation-finding",
    }
)


@dataclass(frozen=True)
class ConstructionRunActivityClassification:
    """Classification of an activity relative to the construction-run boundary."""

    stage: str
    run_type: str
    allowed_in_construction_run: bool


def classify_construction_run_activity(
    *,
    stage: str,
) -> ConstructionRunActivityClassification:
    """Classify whether a stage belongs in a constraint-construction run."""
    if stage in CONSTRUCTION_STAGES:
        return ConstructionRunActivityClassification(
            stage=stage,
            run_type="constraint-construction",
            allowed_in_construction_run=True,
        )

    if stage in VALIDATION_EXECUTION_STAGES:
        return ConstructionRunActivityClassification(
            stage=stage,
            run_type="validation-execution",
            allowed_in_construction_run=False,
        )

    raise ValueError(f"Unknown construction or validation stage: {stage}")


@dataclass(frozen=True)
class ActiveConstructionRunGraphPersistence:
    """Persistence result for one active constraint-construction run graph."""

    run_id: str
    output_path: Path
    graph_state: str
    persisted: bool


def persist_active_construction_run_graph(
    *,
    graph,
    run_id: str,
    output_path: str | Path,
) -> ActiveConstructionRunGraphPersistence:
    """
    Persist the current state of one active construction run as Turtle.

    Repeated calls for the same run and output path replace the on-disk
    serialization with the graph's current state. This keeps one persistent
    RDF results graph current as construction events complete.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    graph.serialize(destination=path, format="turtle")

    return ActiveConstructionRunGraphPersistence(
        run_id=run_id,
        output_path=path,
        graph_state="active",
        persisted=path.exists(),
    )


@dataclass(frozen=True)
class CompletedConstructionRunGraphPersistence:
    """Persistence result for one frozen completed construction-run graph."""

    run_id: str
    output_path: Path
    graph_state: str
    frozen: bool


def freeze_completed_construction_run_graph(
    *,
    graph,
    run_id: str,
    output_path: str | Path,
) -> CompletedConstructionRunGraphPersistence:
    """
    Persist a completed construction-run graph once and then freeze it.

    If the target file already exists, its RDF content must be identical to the
    graph being supplied. A different graph is rejected so completed
    construction history cannot be silently rewritten.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists():
        existing_graph = graph.__class__()
        existing_graph.parse(path, format="turtle")

        if not existing_graph.isomorphic(graph):
            raise ValueError("completed construction-run graph is frozen")

        return CompletedConstructionRunGraphPersistence(
            run_id=run_id,
            output_path=path,
            graph_state="completed",
            frozen=True,
        )

    graph.serialize(destination=path, format="turtle")

    return CompletedConstructionRunGraphPersistence(
        run_id=run_id,
        output_path=path,
        graph_state="completed",
        frozen=True,
    )


@dataclass(frozen=True)
class ConstructionProvenanceRecord:
    """Common construction provenance represented using PROV-O."""

    activity_id: str
    agent_id: str
    used_knowledge_ids: list[str]
    generated_knowledge_ids: list[str]


def record_construction_provenance(
    *,
    graph,
    activity_id: str,
    agent_id: str,
    used_knowledge_ids: list[str],
    generated_knowledge_ids: list[str],
) -> ConstructionProvenanceRecord:
    """Record common execution and provenance relationships using PROV-O."""
    activity = URIRef(activity_id)
    agent = URIRef(agent_id)

    graph.add((activity, RDF.type, PROV.Activity))
    graph.add((agent, RDF.type, PROV.Agent))
    graph.add((activity, PROV.wasAssociatedWith, agent))

    for knowledge_id in used_knowledge_ids:
        knowledge = URIRef(knowledge_id)
        graph.add((knowledge, RDF.type, PROV.Entity))
        graph.add((activity, PROV.used, knowledge))

    for knowledge_id in generated_knowledge_ids:
        knowledge = URIRef(knowledge_id)
        graph.add((knowledge, RDF.type, PROV.Entity))
        graph.add((knowledge, PROV.wasGeneratedBy, activity))

    return ConstructionProvenanceRecord(
        activity_id=activity_id,
        agent_id=agent_id,
        used_knowledge_ids=list(used_knowledge_ids),
        generated_knowledge_ids=list(generated_knowledge_ids),
    )


__all__ = [
    "ConstraintConstructionRunRecord",
    "ConstructionActivityTimingRecord",
    "SharedConstructionKnowledgeRelationship",
    "ConstructionRunActivityClassification",
    "ActiveConstructionRunGraphPersistence",
    "CompletedConstructionRunGraphPersistence",
    "ConstructionProvenanceRecord",
    "create_constraint_construction_run",
    "record_construction_activity_timing",
    "link_shared_construction_knowledge",
    "classify_construction_run_activity",
    "persist_active_construction_run_graph",
    "freeze_completed_construction_run_graph",
    "record_construction_provenance",
]
