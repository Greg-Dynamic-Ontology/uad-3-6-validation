"""Process governed constraints through one bounded construction stage."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable


ConstraintRecord = dict[str, object]
StageExecutor = Callable[[ConstraintRecord], None]


@dataclass(frozen=True)
class ConstraintStageException:
    """Record one constraint that could not complete a construction stage."""

    constraint_id: str
    stage_name: str
    reason: str


@dataclass(frozen=True)
class ConstraintBatchStageResult:
    """Outcome of processing one bounded batch at one construction stage."""

    processed_ids: list[str]
    verification_eligible_ids: list[str]
    exceptions: list[ConstraintStageException]


def process_constraint_batch_stage(
    *,
    constraints: Iterable[ConstraintRecord],
    stage_name: str,
    execute_stage: StageExecutor,
) -> ConstraintBatchStageResult:
    """
    Process every eligible constraint at one construction stage.

    Successfully processed constraints become eligible for verification.
    A failing constraint is recorded as an exception and does not prevent
    remaining eligible constraints from being processed.
    """
    processed_ids: list[str] = []
    verification_eligible_ids: list[str] = []
    exceptions: list[ConstraintStageException] = []

    for constraint in constraints:
        if not bool(constraint.get("eligible", False)):
            continue

        constraint_id = str(constraint["otdd_id"])

        try:
            execute_stage(constraint)
        except Exception as exc:
            exceptions.append(
                ConstraintStageException(
                    constraint_id=constraint_id,
                    stage_name=stage_name,
                    reason=str(exc),
                )
            )
            continue

        processed_ids.append(constraint_id)
        verification_eligible_ids.append(constraint_id)

    return ConstraintBatchStageResult(
        processed_ids=processed_ids,
        verification_eligible_ids=verification_eligible_ids,
        exceptions=exceptions,
    )


__all__ = [
    "ConstraintBatchStageResult",
    "ConstraintStageException",
    "process_constraint_batch_stage",
]
