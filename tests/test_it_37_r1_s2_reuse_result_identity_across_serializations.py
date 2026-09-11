"""IT-37R1S2 — reuse the same governed result identity across serializations."""

from __future__ import annotations

from importlib import import_module

from rdflib import Graph, Namespace, RDF, URIRef


UADEX = Namespace("https://dynamicontology.com/uad36/construction-exchange#")


def _load_exchange_result_recorder():
    """Load the governed exchange behavior established by IT-37R1."""
    try:
        module = import_module("app.services.construction_exchange")
    except ModuleNotFoundError:
        return None

    return getattr(module, "record_construction_stage_result", None)


def test_it_37_r1_s2_reuses_same_governed_result_identity_across_serializations(
    tmp_path,
) -> None:
    """
    Feature: Define governed RDF exchange between constraint-construction stages

    Rule: A construction-stage result has an explicit governed identity

    Scenario: Reuse the same governed result identity across serializations
    """
    record_stage_result = _load_exchange_result_recorder()

    assert record_stage_result is not None, (
        "IT-37R1S2 requires "
        "app.services.construction_exchange."
        "record_construction_stage_result"
    )

    graph = Graph()

    first = record_stage_result(
        output_graph=graph,
        constraint_id="0100.0009",
        construction_stage="normalized-constraint-representation",
        construction_status="GREEN",
        result_id=(
            "https://dynamicontology.com/uad36/construction-exchange/"
            "result/it-37-r1-s2-0100.0009-normalization"
        ),
    )

    output_path = tmp_path / "construction-exchange.ttl"
    graph.serialize(destination=output_path, format="turtle")

    reloaded = Graph()
    reloaded.parse(output_path, format="turtle")

    second = record_stage_result(
        output_graph=reloaded,
        constraint_id="0100.0009",
        construction_stage="normalized-constraint-representation",
        construction_status="GREEN",
        result_id=str(first.result_id),
    )

    expected_result_id = URIRef(str(first.result_id))

    assert second.result_id == expected_result_id
    assert (
        expected_result_id,
        RDF.type,
        UADEX.ConstructionStageResult,
    ) in reloaded

    # Re-serializing and reconstructing the same governed result must not
    # mint a second result identity merely because the graph crossed a
    # serialization boundary.
    result_resources = set(
        reloaded.subjects(
            RDF.type,
            UADEX.ConstructionStageResult,
        )
    )
    assert result_resources == {expected_result_id}
