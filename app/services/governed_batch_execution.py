"""Execute governed constraint-production batches from the Batch Knowledge Graph."""

from __future__ import annotations

from dataclasses import dataclass

from rdflib import Literal, Namespace, URIRef


UADCV = Namespace("https://dynamicontology.com/uad36/constraint-vocabulary#")


@dataclass(frozen=True)
class GovernedBatchMaterializationResult:
    """Result of materializing governed source Unique IDs for one batch."""

    batch_id: str
    governed_unique_ids: list[str]
    materialized_count: int


def materialize_governed_batch_members(
    *,
    batch_knowledge_graph,
    batch_results_graph,
    batch_id: str,
    governed_unique_ids: list[str],
) -> GovernedBatchMaterializationResult:
    """
    Materialize the governed Unique IDs selected for one production batch.

    The Batch Knowledge Graph supplies the governed batch identity. The selected
    source Unique IDs are written into the batch-results graph before constraint
    production begins so the execution record explicitly identifies its members.
    """
    batch = URIRef(batch_id)

    if not any(batch_knowledge_graph.triples((batch, None, None))):
        raise ValueError(f"Unknown governed batch: {batch_id}")

    for unique_id in governed_unique_ids:
        batch_results_graph.add(
            (
                batch,
                UADCV.governedUniqueId,
                Literal(unique_id),
            )
        )

    batch_results_graph.add(
        (
            batch,
            UADCV.materializedConstraintCount,
            Literal(len(governed_unique_ids)),
        )
    )

    return GovernedBatchMaterializationResult(
        batch_id=batch_id,
        governed_unique_ids=list(governed_unique_ids),
        materialized_count=len(governed_unique_ids),
    )


__all__ = [
    "GovernedBatchMaterializationResult",
    "materialize_governed_batch_members",
]
