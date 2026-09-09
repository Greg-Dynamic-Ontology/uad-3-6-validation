"""IT-35R2S1 — synchronize persistent batch results as constraint production proceeds."""

from __future__ import annotations

from importlib import import_module

from rdflib import Graph, Literal, Namespace, URIRef


UADCV = Namespace("https://dynamicontology.com/uad36/constraint-vocabulary#")


def _load_batch_results_synchronizer():
    """Load production synchronization behavior after the RED test exists."""
    try:
        module = import_module("app.services.governed_batch_execution")
    except ModuleNotFoundError:
        return None

    return getattr(module, "synchronize_batch_constraint_knowledge", None)


def test_it_35_r2_s1_adds_or_overwrites_constraint_knowledge_and_persists_run(
    tmp_path,
) -> None:
    """
    Feature: Execute governed constraint-production batches from the Batch Knowledge Graph

    Rule: Keep the persistent batch-results graph synchronized with constraint production

    Scenario: Add or overwrite constraint knowledge and persist batch-run knowledge
    as processing proceeds
    """
    synchronize_batch_constraint_knowledge = _load_batch_results_synchronizer()

    assert synchronize_batch_constraint_knowledge is not None, (
        "IT-35R2S1 requires "
        "app.services.governed_batch_execution."
        "synchronize_batch_constraint_knowledge"
    )

    batch_id = URIRef("https://dynamicontology.com/uad36/batch/B2")
    constraint_id = URIRef("https://dynamicontology.com/uad36/constraint/0100.0009")
    output_path = tmp_path / "batch-B2-results.ttl"

    batch_results_graph = Graph()

    first_result = synchronize_batch_constraint_knowledge(
        batch_results_graph=batch_results_graph,
        batch_id=str(batch_id),
        constraint_id=str(constraint_id),
        constraint_knowledge={
            UADCV.stageStatus: Literal("RED"),
            UADCV.constructionStage: Literal("normalized-constraint-representation"),
        },
        output_path=output_path,
    )

    assert first_result.batch_id == str(batch_id)
    assert first_result.constraint_id == str(constraint_id)
    assert first_result.output_path == output_path
    assert first_result.persisted is True

    persisted_first = Graph()
    persisted_first.parse(output_path, format="turtle")

    assert (
        constraint_id,
        UADCV.stageStatus,
        Literal("RED"),
    ) in persisted_first
    assert (
        constraint_id,
        UADCV.constructionStage,
        Literal("normalized-constraint-representation"),
    ) in persisted_first

    # Processing advances. Knowledge for the same predicate is overwritten,
    # while other established knowledge remains in the same persistent graph.
    second_result = synchronize_batch_constraint_knowledge(
        batch_results_graph=batch_results_graph,
        batch_id=str(batch_id),
        constraint_id=str(constraint_id),
        constraint_knowledge={
            UADCV.stageStatus: Literal("GREEN"),
        },
        output_path=output_path,
    )

    assert second_result.output_path == first_result.output_path
    assert second_result.persisted is True

    persisted_second = Graph()
    persisted_second.parse(output_path, format="turtle")

    assert (
        constraint_id,
        UADCV.stageStatus,
        Literal("GREEN"),
    ) in persisted_second
    assert (
        constraint_id,
        UADCV.stageStatus,
        Literal("RED"),
    ) not in persisted_second
    assert (
        constraint_id,
        UADCV.constructionStage,
        Literal("normalized-constraint-representation"),
    ) in persisted_second
