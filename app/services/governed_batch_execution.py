"""Execute governed constraint-production batches from the Batch Knowledge Graph."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

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


@dataclass(frozen=True)
class BatchConstraintSynchronizationResult:
    """Persistence result for one constraint update in a batch-results graph."""

    batch_id: str
    constraint_id: str
    output_path: Path
    persisted: bool


def synchronize_batch_constraint_knowledge(
    *,
    batch_results_graph,
    batch_id: str,
    constraint_id: str,
    constraint_knowledge: dict,
    output_path: str | Path,
) -> BatchConstraintSynchronizationResult:
    """
    Add or overwrite current constraint knowledge and persist the batch-results graph.

    For each supplied predicate, any prior values for that predicate on the same
    constraint are removed before the new value is added. Other established
    constraint knowledge remains unchanged.
    """
    constraint = URIRef(constraint_id)

    for predicate, value in constraint_knowledge.items():
        batch_results_graph.remove((constraint, predicate, None))
        batch_results_graph.add((constraint, predicate, value))

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    batch_results_graph.serialize(destination=path, format="turtle")

    return BatchConstraintSynchronizationResult(
        batch_id=batch_id,
        constraint_id=constraint_id,
        output_path=path,
        persisted=path.exists(),
    )


__all__ = [
    "GovernedBatchMaterializationResult",
    "BatchConstraintSynchronizationResult",
    "materialize_governed_batch_members",
    "synchronize_batch_constraint_knowledge",
]
