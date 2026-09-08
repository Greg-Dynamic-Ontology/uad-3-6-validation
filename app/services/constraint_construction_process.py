"""Advance a governed constraint through required OTDD construction stages."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable


StageExecutor = Callable[[str], dict[str, object]]


@dataclass(frozen=True)
class ConstraintConstructionResult:
    """Outcome of advancing one governed constraint through construction."""

    constraint_id: str
    verified_stages: list[str]
    is_complete: bool
    next_stage: str | None


def advance_constraint_through_construction(
    *,
    constraint_id: str,
    required_stages: Iterable[str],
    execute_stage: StageExecutor,
) -> ConstraintConstructionResult:
    """
    Execute and verify each required construction stage in order.

    Processing stops at the first stage that does not report verified=True.
    A constraint is complete only when every required stage is verified.
    """
    stages = list(required_stages)
    verified_stages: list[str] = []

    for stage_name in stages:
        stage_result = execute_stage(stage_name)

        if str(stage_result.get("stage_name", "")) != stage_name:
            raise ValueError(
                "Construction stage result does not match the requested stage."
            )

        if not bool(stage_result.get("verified", False)):
            return ConstraintConstructionResult(
                constraint_id=constraint_id,
                verified_stages=verified_stages,
                is_complete=False,
                next_stage=stage_name,
            )

        verified_stages.append(stage_name)

    return ConstraintConstructionResult(
        constraint_id=constraint_id,
        verified_stages=verified_stages,
        is_complete=True,
        next_stage=None,
    )


__all__ = [
    "ConstraintConstructionResult",
    "advance_constraint_through_construction",
]
