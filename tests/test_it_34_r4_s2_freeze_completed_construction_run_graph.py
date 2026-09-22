"""IT-34R4S2 — freeze a completed construction-run graph."""

from __future__ import annotations

from importlib import import_module

from rdflib import Graph, Literal, Namespace, RDF, URIRef


UADRUN = Namespace("https://dynamicontology.com/uad36/construction/run-vocabulary#")


def _load_completed_graph_freezer():
    """Load the production freeze behavior after the RED test exists."""
    try:
        module = import_module("app.services.constraint_construction_run")
    except ModuleNotFoundError:
        return None

    return getattr(module, "freeze_completed_construction_run_graph", None)


def test_it_34_r4_s2_freezes_completed_construction_run_graph(tmp_path) -> None:
    """
    Feature: Define and persist governed constraint-construction run knowledge

    Rule: Each constraint-construction execution has its own persistent RDF
    results graph

    Scenario: Freeze a completed construction-run graph
    """
    freeze_completed_construction_run_graph = _load_completed_graph_freezer()

    assert freeze_completed_construction_run_graph is not None, (
        "IT-34R4S2 requires "
        "app.services.constraint_construction_run."
        "freeze_completed_construction_run_graph"
    )

    run_id = URIRef(
        "https://dynamicontology.com/uad36/construction/run/run-001"
    )
    activity_id = URIRef(f"{run_id}/activity/activity-001")
    result_id = URIRef(f"{run_id}/result/result-001")
    output_path = tmp_path / "run-001.ttl"

    graph = Graph()
    graph.add((run_id, RDF.type, UADRUN.ConstraintConstructionRun))
    graph.add((run_id, UADRUN.runState, Literal("completed")))
    graph.add((activity_id, RDF.type, UADRUN.ConstraintConstructionActivity))
    graph.add((activity_id, UADRUN.forRun, run_id))
    graph.add((result_id, RDF.type, UADRUN.ConstraintConstructionResult))
    graph.add((result_id, UADRUN.generatedByActivity, activity_id))
    graph.add((result_id, UADRUN.stageStatus, Literal("GREEN")))

    frozen = freeze_completed_construction_run_graph(
        graph=graph,
        run_id=str(run_id),
        output_path=output_path,
    )

    assert output_path.exists()
    assert frozen.run_id == str(run_id)
    assert frozen.output_path == output_path
    assert frozen.graph_state == "completed"
    assert frozen.frozen is True

    persisted = Graph()
    persisted.parse(output_path, format="turtle")

    assert (run_id, UADRUN.runState, Literal("completed")) in persisted
    assert (
        result_id,
        UADRUN.generatedByActivity,
        activity_id,
    ) in persisted

    # A completed run is immutable. A later attempt to replace its graph
    # must fail rather than silently rewriting construction history.
    changed_graph = Graph()
    for triple in graph:
        changed_graph.add(triple)
    changed_graph.add(
        (
            run_id,
            UADRUN.exceptionReason,
            Literal("late mutation"),
        )
    )

    try:
        freeze_completed_construction_run_graph(
            graph=changed_graph,
            run_id=str(run_id),
            output_path=output_path,
        )
    except ValueError as exc:
        assert "completed construction-run graph is frozen" in str(exc)
    else:
        raise AssertionError(
            "IT-34R4S2 requires a completed construction-run graph "
            "to reject later replacement"
        )

    persisted_after_rejected_change = Graph()
    persisted_after_rejected_change.parse(output_path, format="turtle")

    assert (
        run_id,
        UADRUN.exceptionReason,
        Literal("late mutation"),
    ) not in persisted_after_rejected_change
