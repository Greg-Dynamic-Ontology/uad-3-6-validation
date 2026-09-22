"""IT-34R5S1 — represent common provenance using PROV-O."""

from __future__ import annotations

from importlib import import_module

from rdflib import Graph, Namespace, RDF, URIRef


PROV = Namespace("http://www.w3.org/ns/prov#")


def _load_provenance_recorder():
    """Load the production PROV-O behavior after the RED test exists."""
    try:
        module = import_module("app.services.constraint_construction_run")
    except ModuleNotFoundError:
        return None

    return getattr(module, "record_construction_provenance", None)


def test_it_34_r5_s1_represents_common_provenance_using_prov_o() -> None:
    """
    Feature: Define and persist governed constraint-construction run knowledge

    Rule: Reuse PROV-O for common execution and provenance semantics

    Scenario: Represent common provenance using PROV-O
    """
    record_construction_provenance = _load_provenance_recorder()

    assert record_construction_provenance is not None, (
        "IT-34R5S1 requires "
        "app.services.constraint_construction_run."
        "record_construction_provenance"
    )

    activity_id = URIRef(
        "https://dynamicontology.com/uad36/construction/run/run-001/"
        "activity/context-resolution-001"
    )
    agent_id = URIRef(
        "https://dynamicontology.com/uad36/agent/context-resolution"
    )
    used_knowledge_id = URIRef(
        "https://dynamicontology.com/uad36/constraint/0100.0007"
    )
    generated_knowledge_id = URIRef(
        "https://dynamicontology.com/uad36/construction/run/run-001/"
        "result/context-resolution-001"
    )

    graph = Graph()

    result = record_construction_provenance(
        graph=graph,
        activity_id=str(activity_id),
        agent_id=str(agent_id),
        used_knowledge_ids=[str(used_knowledge_id)],
        generated_knowledge_ids=[str(generated_knowledge_id)],
    )

    assert result.activity_id == str(activity_id)
    assert result.agent_id == str(agent_id)
    assert result.used_knowledge_ids == [str(used_knowledge_id)]
    assert result.generated_knowledge_ids == [str(generated_knowledge_id)]

    # Common execution and provenance semantics use PROV-O directly.
    assert (activity_id, RDF.type, PROV.Activity) in graph
    assert (agent_id, RDF.type, PROV.Agent) in graph
    assert (used_knowledge_id, RDF.type, PROV.Entity) in graph
    assert (generated_knowledge_id, RDF.type, PROV.Entity) in graph

    assert (activity_id, PROV.wasAssociatedWith, agent_id) in graph
    assert (activity_id, PROV.used, used_knowledge_id) in graph
    assert (
        generated_knowledge_id,
        PROV.wasGeneratedBy,
        activity_id,
    ) in graph
