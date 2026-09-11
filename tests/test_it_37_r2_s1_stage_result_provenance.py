"""IT-37R2S1 — link a stage result to the activity that generated it."""

from __future__ import annotations

from importlib import import_module

from rdflib import Graph, Namespace, RDF, URIRef
from rdflib.namespace import PROV


UADEX = Namespace("https://dynamicontology.com/uad36/construction-exchange#")


def _load_provenance_linker():
    """Load the governed construction-exchange provenance behavior after RED exists."""
    try:
        module = import_module("app.services.construction_exchange")
    except ModuleNotFoundError:
        return None

    return getattr(module, "record_construction_stage_provenance", None)


def test_it_37_r2_s1_links_stage_result_to_generating_activity() -> None:
    """
    Feature: Define governed RDF exchange between constraint-construction stages

    Rule: Exchange knowledge preserves its construction provenance

    Scenario: Link a stage result to the activity that generated it
    """
    record_stage_provenance = _load_provenance_linker()

    assert record_stage_provenance is not None, (
        "IT-37R2S1 requires "
        "app.services.construction_exchange."
        "record_construction_stage_provenance"
    )

    graph = Graph()

    result_id = URIRef(
        "https://dynamicontology.com/uad36/construction-exchange/"
        "result/0100.0009-normalization"
    )
    activity_id = URIRef(
        "https://dynamicontology.com/uad36/construction-exchange/"
        "activity/0100.0009-normalization"
    )
    agent_id = URIRef(
        "https://dynamicontology.com/uad36/agent/normalization"
    )
    used_knowledge_id = URIRef(
        "https://dynamicontology.com/uad36/constraint/0100.0009"
    )

    result = record_stage_provenance(
        output_graph=graph,
        result_id=str(result_id),
        activity_id=str(activity_id),
        agent_id=str(agent_id),
        used_knowledge_ids=[str(used_knowledge_id)],
    )

    assert result.result_id == result_id
    assert result.activity_id == activity_id
    assert result.agent_id == agent_id
    assert result.used_knowledge_ids == (used_knowledge_id,)

    assert (
        result_id,
        PROV.wasGeneratedBy,
        activity_id,
    ) in graph
    assert (
        activity_id,
        RDF.type,
        PROV.Activity,
    ) in graph
    assert (
        activity_id,
        PROV.wasAssociatedWith,
        agent_id,
    ) in graph
    assert (
        agent_id,
        RDF.type,
        PROV.Agent,
    ) in graph
    assert (
        activity_id,
        PROV.used,
        used_knowledge_id,
    ) in graph
    assert (
        used_knowledge_id,
        RDF.type,
        PROV.Entity,
    ) in graph
