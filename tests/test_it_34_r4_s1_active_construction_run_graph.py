"""IT-34R4S1 — keep an active construction-run graph current on disk."""

from __future__ import annotations

from importlib import import_module

from rdflib import Graph, Literal, Namespace, RDF, URIRef


UADRUN = Namespace("https://dynamicontology.com/uad36/construction/run-vocabulary#")


def _load_active_graph_persister():
    """Load the production persistence behavior after the RED test exists."""
    try:
        module = import_module("app.services.constraint_construction_run")
    except ModuleNotFoundError:
        return None

    return getattr(module, "persist_active_construction_run_graph", None)


def test_it_34_r4_s1_keeps_active_construction_run_graph_current_on_disk(
    tmp_path,
) -> None:
    """
    Feature: Define and persist governed constraint-construction run knowledge

    Rule: Each constraint-construction execution has its own persistent RDF
    results graph

    Scenario: Keep an active construction-run graph current on disk
    """
    persist_active_construction_run_graph = _load_active_graph_persister()

    assert persist_active_construction_run_graph is not None, (
        "IT-34R4S1 requires "
        "app.services.constraint_construction_run."
        "persist_active_construction_run_graph"
    )

    run_id = URIRef(
        "https://dynamicontology.com/uad36/construction/run/run-001"
    )
    activity_id = URIRef(f"{run_id}/activity/activity-001")
    result_id = URIRef(f"{run_id}/result/result-001")
    output_path = tmp_path / "run-001.ttl"

    graph = Graph()
    graph.add((run_id, RDF.type, UADRUN.ConstraintConstructionRun))
    graph.add((activity_id, RDF.type, UADRUN.ConstraintConstructionActivity))
    graph.add((activity_id, UADRUN.forRun, run_id))

    first_write = persist_active_construction_run_graph(
        graph=graph,
        run_id=str(run_id),
        output_path=output_path,
    )

    assert output_path.exists()
    assert first_write.run_id == str(run_id)
    assert first_write.output_path == output_path
    assert first_write.graph_state == "active"
    assert first_write.persisted is True

    persisted_after_first_write = Graph()
    persisted_after_first_write.parse(output_path, format="turtle")

    assert (run_id, RDF.type, UADRUN.ConstraintConstructionRun) in persisted_after_first_write
    assert (
        activity_id,
        RDF.type,
        UADRUN.ConstraintConstructionActivity,
    ) in persisted_after_first_write

    # A later completed event is added to the same active run graph.
    graph.add((result_id, RDF.type, UADRUN.ConstraintConstructionResult))
    graph.add((result_id, UADRUN.generatedByActivity, activity_id))
    graph.add((result_id, UADRUN.stageStatus, Literal("GREEN")))

    second_write = persist_active_construction_run_graph(
        graph=graph,
        run_id=str(run_id),
        output_path=output_path,
    )

    assert second_write.run_id == str(run_id)
    assert second_write.output_path == output_path
    assert second_write.graph_state == "active"
    assert second_write.persisted is True

    persisted_after_second_write = Graph()
    persisted_after_second_write.parse(output_path, format="turtle")

    assert (result_id, RDF.type, UADRUN.ConstraintConstructionResult) in persisted_after_second_write
    assert (
        result_id,
        UADRUN.generatedByActivity,
        activity_id,
    ) in persisted_after_second_write
    assert (result_id, UADRUN.stageStatus, Literal("GREEN")) in persisted_after_second_write

    # The persistent graph represents this run and its latest completed event,
    # rather than creating a second graph merely because the run was updated.
    assert first_write.output_path == second_write.output_path
    assert len(persisted_after_second_write) > len(persisted_after_first_write)
