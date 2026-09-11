"""Governed RDF exchange between constraint-construction stages."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

from rdflib import Graph, Literal, Namespace, RDF, URIRef
from rdflib.namespace import PROV


UADCON = Namespace("https://dynamicontology.com/uad36/constraint/")
UADEX = Namespace("https://dynamicontology.com/uad36/construction-exchange#")
UADRESULT_BASE = "https://dynamicontology.com/uad36/construction-exchange/result/"


@dataclass(frozen=True)
class ConstructionStageResultRecord:
    """Governed identity and common exchange metadata for one stage result."""

    result_id: URIRef
    constraint_id: str
    construction_stage: str
    construction_status: str


def record_construction_stage_result(
    *,
    output_graph: Graph,
    constraint_id: str,
    construction_stage: str,
    construction_status: str,
) -> ConstructionStageResultRecord:
    """Represent one construction-stage result as governed RDF."""
    if not constraint_id.strip():
        raise ValueError("constraint_id is required")
    if not construction_stage.strip():
        raise ValueError("construction_stage is required")
    if not construction_status.strip():
        raise ValueError("construction_status is required")

    result_id = URIRef(f"{UADRESULT_BASE}{uuid4().hex}")
    constraint_iri = URIRef(f"{UADCON}{constraint_id}")

    output_graph.add(
        (result_id, RDF.type, UADEX.ConstructionStageResult)
    )
    output_graph.add(
        (result_id, UADEX.forConstraint, constraint_iri)
    )
    output_graph.add(
        (
            result_id,
            UADEX.constructionStage,
            Literal(construction_stage),
        )
    )
    output_graph.add(
        (
            result_id,
            UADEX.constructionStatus,
            Literal(construction_status),
        )
    )

    return ConstructionStageResultRecord(
        result_id=result_id,
        constraint_id=constraint_id,
        construction_stage=construction_stage,
        construction_status=construction_status,
    )


@dataclass(frozen=True)
class ConstructionStageProvenanceRecord:
    """PROV-O provenance for one governed construction-stage result."""

    result_id: URIRef
    activity_id: URIRef
    agent_id: URIRef
    used_knowledge_ids: tuple[URIRef, ...]


def record_construction_stage_provenance(
    *,
    output_graph: Graph,
    result_id: str,
    activity_id: str,
    agent_id: str,
    used_knowledge_ids: list[str],
) -> ConstructionStageProvenanceRecord:
    """Record the provenance chain for one construction-stage result."""
    result = URIRef(result_id)
    activity = URIRef(activity_id)
    agent = URIRef(agent_id)
    used_knowledge = tuple(URIRef(value) for value in used_knowledge_ids)

    output_graph.add((result, PROV.wasGeneratedBy, activity))
    output_graph.add((activity, RDF.type, PROV.Activity))
    output_graph.add((activity, PROV.wasAssociatedWith, agent))
    output_graph.add((agent, RDF.type, PROV.Agent))

    for knowledge in used_knowledge:
        output_graph.add((activity, PROV.used, knowledge))
        output_graph.add((knowledge, RDF.type, PROV.Entity))

    return ConstructionStageProvenanceRecord(
        result_id=result,
        activity_id=activity,
        agent_id=agent,
        used_knowledge_ids=used_knowledge,
    )


@dataclass(frozen=True)
class ConstructionStageTimingRecord:
    """PROV-O timing for one governed construction activity."""

    activity_id: URIRef
    started_at: datetime
    ended_at: datetime


def record_construction_stage_timing(
    *,
    output_graph: Graph,
    activity_id: str,
    started_at: datetime,
    ended_at: datetime,
) -> ConstructionStageTimingRecord:
    """Record construction activity start and end times in the exchange graph."""
    if ended_at < started_at:
        raise ValueError("ended_at cannot be earlier than started_at")

    activity = URIRef(activity_id)

    output_graph.add(
        (
            activity,
            PROV.startedAtTime,
            Literal(started_at, datatype=URIRef("http://www.w3.org/2001/XMLSchema#dateTime")),
        )
    )
    output_graph.add(
        (
            activity,
            PROV.endedAtTime,
            Literal(ended_at, datatype=URIRef("http://www.w3.org/2001/XMLSchema#dateTime")),
        )
    )

    return ConstructionStageTimingRecord(
        activity_id=activity,
        started_at=started_at,
        ended_at=ended_at,
    )


__all__ = [
    "ConstructionStageResultRecord",
    "ConstructionStageProvenanceRecord",
    "ConstructionStageTimingRecord",
    "record_construction_stage_result",
    "record_construction_stage_provenance",
    "record_construction_stage_timing",
]
