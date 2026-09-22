"""Resume a governed constraint after its exception has been resolved."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence


@dataclass(frozen=True)
class ConstraintResumeResult:
    """Outcome of resuming a previously unresolved governed constraint."""

    constraint_id: str
    otdd_id: str
    resume_stage: str
    resolution: Mapping[str, object]
    preserved_verified_stages: list[str]
    status: str
    requires_review: bool
    eligible_for_automated_production: bool


def resume_resolved_constraint(
    *,
    exception_record: Mapping[str, object],
    resolution: Mapping[str, object],
    previously_verified_stages: Sequence[str],
) -> ConstraintResumeResult:
    """
    Resume processing from the unresolved construction stage.

    Previously verified stages remain verified and are not reconstructed.
    The supplied resolution is retained as the knowledge that permits the
    constraint to re-enter automated production.
    """
    if str(exception_record.get("status", "")) != "exception":
        raise ValueError(
            "Only a constraint currently recorded as an exception can resume."
        )

    if not resolution:
        raise ValueError(
            "A resolved exception must include the knowledge that resolved it."
        )

    resume_stage = str(exception_record["stage_name"])

    return ConstraintResumeResult(
        constraint_id=str(exception_record["constraint_id"]),
        otdd_id=str(exception_record["otdd_id"]),
        resume_stage=resume_stage,
        resolution=dict(resolution),
        preserved_verified_stages=list(previously_verified_stages),
        status="resolved",
        requires_review=False,
        eligible_for_automated_production=True,
    )


__all__ = [
    "ConstraintResumeResult",
    "resume_resolved_constraint",
]
