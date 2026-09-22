"""Route unresolved governed constraints into an explicit review queue."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class ConstraintExceptionRecord:
    """Recorded exception for a governed constraint that cannot continue automatically."""

    constraint_id: str
    otdd_id: str
    stage_name: str
    reason: str
    requires_review: bool
    eligible_for_automated_production: bool
    status: str


def route_unresolved_constraint(
    *,
    constraint: Mapping[str, object],
    stage_name: str,
    reason: str,
) -> ConstraintExceptionRecord:
    """
    Route an unresolved governed constraint for review.

    The constraint remains identified and traceable, records the stage and
    reason for failure, and is blocked from further automated production
    until the exception is resolved.
    """
    return ConstraintExceptionRecord(
        constraint_id=str(constraint["constraint_id"]),
        otdd_id=str(constraint["otdd_id"]),
        stage_name=stage_name,
        reason=reason,
        requires_review=True,
        eligible_for_automated_production=False,
        status="exception",
    )


__all__ = [
    "ConstraintExceptionRecord",
    "route_unresolved_constraint",
]
