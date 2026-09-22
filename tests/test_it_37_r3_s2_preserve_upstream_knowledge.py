"""IT-37R3S2 — preserve upstream knowledge when a downstream result is produced."""

from __future__ import annotations

from importlib import import_module

from rdflib import Graph, Literal, Namespace, RDF, URIRef
from rdflib.namespace import PROV


UADEX = Namespace("https://dynamicontology.com/uad36/construction-exchange#")


def _load_downstream_result_recorder():
    """Load downstream result production behavior after RED exists."""
    try:
        module = import_module("app.services.construction_exchange")
    except ModuleNotFoundError:
        return None

    return getattr(module, "record_downstream_stage_result", None)


def test_it_37_r3_s2_preserves_upstream_knowledge_when_downstream_result_is_produced() -> None:
    """
    Feature: Define governed RDF exchange between constraint-construction stages

    Rule: A downstream stage consumes governed RDF rather than an upstream
    implementation object

    Scenario: Preserve upstream knowledge when a downstream result is produced
    """
    record_downstream_result = _load_downstream_result_recorder()

    assert record_downstream_result is not None, (
        "IT-37R3S2 requires "
        "app.services.construction_exchange."
        "record_downstream_stage_result"
    )

    graph = Graph()

    constraint_id = URIRef(
        "https://dynamicontology.com/uad36/constraint/0100.0009"
    )
    upstream_result_id = URIRef(
        "https://dynamicontology.com/uad36/construction-exchange/"
        "result/0100.0009-normalization"
    )
    upstream_activity_id = URIRef(
        "https://dynamicontology.com/uad36/construction-exchange/"
        "activity/0100.0009-normalization"
    )
    downstream_activity_id = URIRef(
        "https://dynamicontology.com/uad36/construction-exchange/"
        "activity/0100.0009-logical-schema-binding"
    )

    graph.add((upstream_result_id, RDF.type, UADEX.ConstructionStageResult))
    graph.add((upstream_result_id, UADEX.forConstraint, constraint_id))
    graph.add(
        (
            upstream_result_id,
            UADEX.constructionStage,
            Literal("normalized-constraint-representation"),
        )
    )
    graph.add((upstream_result_id, PROV.wasGeneratedBy, upstream_activity_id))
    graph.add((upstream_activity_id, RDF.type, PROV.Activity))
    graph.add((downstream_activity_id, RDF.type, PROV.Activity))
    graph.add((downstream_activity_id, PROV.used, upstream_result_id))

    upstream_before = set(graph.triples((upstream_result_id, None, None)))

    result = record_downstream_result(
        exchange_graph=graph,
        constraint_id="0100.0009",
        construction_stage="logical-schema-binding",
        construction_status="GREEN",
        downstream_activity_id=str(downstream_activity_id),
        upstream_result_id=str(upstream_result_id),
    )

    downstream_result_id = URIRef(str(result.result_id))

    assert downstream_result_id != upstream_result_id

    assert upstream_before.issubset(
        set(graph.triples((upstream_result_id, None, None)))
    )

    assert (
        downstream_result_id,
        RDF.type,
        UADEX.ConstructionStageResult,
    ) in graph
    assert (
        downstream_result_id,
        UADEX.forConstraint,
        constraint_id,
    ) in graph
    assert (
        downstream_result_id,
        PROV.wasGeneratedBy,
        downstream_activity_id,
    ) in graph
    assert (
        downstream_activity_id,
        PROV.used,
        upstream_result_id,
    ) in graph
