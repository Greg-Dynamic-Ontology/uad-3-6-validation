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
    available_for_downstream: bool = False
    exception_reason: str | None = None
    requires_review: bool = False


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


@dataclass(frozen=True)
class DownstreamStageInputRecord:
    """Governed RDF identity used as input by a downstream construction activity."""

    downstream_activity_id: URIRef
    upstream_result_id: URIRef


def record_downstream_stage_input(
    *,
    exchange_graph: Graph,
    downstream_activity_id: str,
    upstream_result_id: str,
) -> DownstreamStageInputRecord:
    """Record that a downstream construction activity uses an upstream RDF result."""
    downstream_activity = URIRef(downstream_activity_id)
    upstream_result = URIRef(upstream_result_id)

    if (
        upstream_result,
        RDF.type,
        UADEX.ConstructionStageResult,
    ) not in exchange_graph:
        raise ValueError(
            "upstream_result_id must identify a ConstructionStageResult "
            "present in the exchange graph"
        )

    exchange_graph.add(
        (
            downstream_activity,
            RDF.type,
            PROV.Activity,
        )
    )
    exchange_graph.add(
        (
            downstream_activity,
            PROV.used,
            upstream_result,
        )
    )

    return DownstreamStageInputRecord(
        downstream_activity_id=downstream_activity,
        upstream_result_id=upstream_result,
    )


def record_downstream_stage_result(
    *,
    exchange_graph: Graph,
    constraint_id: str,
    construction_stage: str,
    construction_status: str,
    downstream_activity_id: str,
    upstream_result_id: str,
) -> ConstructionStageResultRecord:
    """Produce a downstream result while preserving its governed upstream knowledge."""
    downstream_activity = URIRef(downstream_activity_id)
    upstream_result = URIRef(upstream_result_id)

    if (
        upstream_result,
        RDF.type,
        UADEX.ConstructionStageResult,
    ) not in exchange_graph:
        raise ValueError(
            "upstream_result_id must identify a ConstructionStageResult "
            "present in the exchange graph"
        )

    if (
        downstream_activity,
        PROV.used,
        upstream_result,
    ) not in exchange_graph:
        raise ValueError(
            "downstream activity must use the governed upstream result "
            "before producing its result"
        )

    downstream_result = record_construction_stage_result(
        output_graph=exchange_graph,
        constraint_id=constraint_id,
        construction_stage=construction_stage,
        construction_status=construction_status,
    )

    exchange_graph.add(
        (
            downstream_result.result_id,
            PROV.wasGeneratedBy,
            downstream_activity,
        )
    )

    return downstream_result


def exchange_successful_construction_stage_result(
    *,
    exchange_graph: Graph,
    constraint_id: str,
    construction_stage: str,
) -> ConstructionStageResultRecord:
    """Record a GREEN stage result as available for downstream consumption."""
    stage_result = record_construction_stage_result(
        output_graph=exchange_graph,
        constraint_id=constraint_id,
        construction_stage=construction_stage,
        construction_status="GREEN",
    )

    exchange_graph.add(
        (
            stage_result.result_id,
            UADEX.availableForDownstream,
            Literal(True),
        )
    )

    return ConstructionStageResultRecord(
        result_id=stage_result.result_id,
        constraint_id=stage_result.constraint_id,
        construction_stage=stage_result.construction_stage,
        construction_status=stage_result.construction_status,
        available_for_downstream=True,
    )


def exchange_construction_stage_exception(
    *,
    exchange_graph: Graph,
    constraint_id: str,
    construction_stage: str,
    exception_reason: str,
    requires_review: bool,
) -> ConstructionStageResultRecord:
    """Record governed exception knowledge instead of inventing successful output."""
    if not exception_reason.strip():
        raise ValueError("exception_reason is required")

    stage_result = record_construction_stage_result(
        output_graph=exchange_graph,
        constraint_id=constraint_id,
        construction_stage=construction_stage,
        construction_status="EXCEPTION",
    )

    exchange_graph.add(
        (
            stage_result.result_id,
            UADEX.exceptionReason,
            Literal(exception_reason),
        )
    )
    exchange_graph.add(
        (
            stage_result.result_id,
            UADEX.requiresReview,
            Literal(requires_review),
        )
    )
    exchange_graph.add(
        (
            stage_result.result_id,
            UADEX.availableForDownstream,
            Literal(False),
        )
    )

    return ConstructionStageResultRecord(
        result_id=stage_result.result_id,
        constraint_id=stage_result.constraint_id,
        construction_stage=stage_result.construction_stage,
        construction_status=stage_result.construction_status,
        available_for_downstream=False,
        exception_reason=exception_reason,
        requires_review=requires_review,
    )


__all__ = [
    "ConstructionStageResultRecord",
    "ConstructionStageProvenanceRecord",
    "ConstructionStageTimingRecord",
    "DownstreamStageInputRecord",
    "record_construction_stage_result",
    "record_construction_stage_provenance",
    "record_construction_stage_timing",
    "record_downstream_stage_input",
    "record_downstream_stage_result",
    "exchange_successful_construction_stage_result",
    "exchange_construction_stage_exception",
]
