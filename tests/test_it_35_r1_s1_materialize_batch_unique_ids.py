"""IT-35R1S1 — write governed Unique IDs for a batch into the batch-results RDF graph."""

from __future__ import annotations

from importlib import import_module

from rdflib import Graph, Literal, Namespace, RDF, URIRef


UADBATCH = Namespace("https://dynamicontology.com/uad36/batch/")
UADCV = Namespace("https://dynamicontology.com/uad36/constraint-vocabulary#")


def _load_batch_member_materializer():
    """Load the production batch-member materialization behavior after RED exists."""
    try:
        module = import_module("app.services.governed_batch_execution")
    except ModuleNotFoundError:
        return None

    return getattr(module, "materialize_governed_batch_members", None)


def test_it_35_r1_s1_writes_governed_unique_ids_into_batch_results_graph() -> None:
    """
    Feature: Execute governed constraint-production batches from the Batch Knowledge Graph

    Rule: Materialize the governed members of a batch before constraint production begins

    Scenario: Write the governed Unique IDs for a batch into the batch-results RDF graph
    """
    materialize_governed_batch_members = _load_batch_member_materializer()

    assert materialize_governed_batch_members is not None, (
        "IT-35R1S1 requires "
        "app.services.governed_batch_execution."
        "materialize_governed_batch_members"
    )

    batch_id = URIRef(f"{UADBATCH}B2")
    source_constraint_ids = ["0100.0009", "0100.0010"]

    batch_knowledge_graph = Graph()
    batch_knowledge_graph.add((batch_id, RDF.type, UADCV.GovernedConstraintBatch))
    batch_knowledge_graph.add(
        (batch_id, UADCV.intendedConstraintCount, Literal(2))
    )
    batch_knowledge_graph.add(
        (batch_id, UADCV.firstConstraintOrdinal, Literal(2))
    )
    batch_knowledge_graph.add(
        (batch_id, UADCV.lastConstraintOrdinal, Literal(3))
    )

    batch_results_graph = Graph()

    result = materialize_governed_batch_members(
        batch_knowledge_graph=batch_knowledge_graph,
        batch_results_graph=batch_results_graph,
        batch_id=str(batch_id),
        governed_unique_ids=source_constraint_ids,
    )

    assert result.batch_id == str(batch_id)
    assert result.governed_unique_ids == source_constraint_ids
    assert result.materialized_count == 2

    # The batch-results graph records the governed source Unique IDs themselves.
    for unique_id in source_constraint_ids:
        assert (
            batch_id,
            UADCV.governedUniqueId,
            Literal(unique_id),
        ) in batch_results_graph

    # Membership is materialized before production; the expected count is preserved.
    assert (
        batch_id,
        UADCV.materializedConstraintCount,
        Literal(2),
    ) in batch_results_graph
