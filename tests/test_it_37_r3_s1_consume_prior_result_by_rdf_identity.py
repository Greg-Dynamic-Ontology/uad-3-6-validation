"""IT-37R3S1 — consume a prior stage result through RDF identity."""

from __future__ import annotations

from importlib import import_module

from rdflib import Graph, Namespace, RDF, URIRef
from rdflib.namespace import PROV


UADEX = Namespace("https://dynamicontology.com/uad36/construction-exchange#")


def _load_stage_input_recorder():
    """Load the governed downstream-input behavior after RED exists."""
    try:
        module = import_module("app.services.construction_exchange")
    except ModuleNotFoundError:
        return None

    return getattr(module, "record_downstream_stage_input", None)


def test_it_37_r3_s1_consumes_prior_stage_result_through_rdf_identity() -> None:
    """
    Feature: Define governed RDF exchange between constraint-construction stages

    Rule: A downstream stage consumes governed RDF rather than an upstream
    implementation object

    Scenario: Consume a prior stage result through RDF identity
    """
    record_downstream_input = _load_stage_input_recorder()

    assert record_downstream_input is not None, (
        "IT-37R3S1 requires "
        "app.services.construction_exchange."
        "record_downstream_stage_input"
    )

    graph = Graph()

    upstream_result_id = URIRef(
        "https://dynamicontology.com/uad36/construction-exchange/"
        "result/0100.0009-normalization"
    )
    downstream_activity_id = URIRef(
        "https://dynamicontology.com/uad36/construction-exchange/"
        "activity/0100.0009-logical-schema-binding"
    )

    graph.add(
        (
            upstream_result_id,
            RDF.type,
            UADEX.ConstructionStageResult,
        )
    )

    result = record_downstream_input(
        exchange_graph=graph,
        downstream_activity_id=str(downstream_activity_id),
        upstream_result_id=str(upstream_result_id),
    )

    assert result.downstream_activity_id == downstream_activity_id
    assert result.upstream_result_id == upstream_result_id

    assert (
        downstream_activity_id,
        RDF.type,
        PROV.Activity,
    ) in graph
    assert (
        downstream_activity_id,
        PROV.used,
        upstream_result_id,
    ) in graph

    # The governed inter-stage contract is the upstream RDF resource itself.
    # No Python result object is passed as the upstream stage input.
    assert isinstance(result.upstream_result_id, URIRef)
