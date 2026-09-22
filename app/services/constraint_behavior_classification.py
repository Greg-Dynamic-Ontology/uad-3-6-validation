"""Classify governed constraint behavior without forcing unknown patterns."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class ConstraintBehaviorClassification:
    """Classification result for one governed constraint."""

    constraint_id: str
    matched_behavior_id: str | None
    is_previously_unknown: bool
    proposed_behavior_id: str | None
    requires_governance: bool
    eligible_for_repeated_implementation: bool


def classify_constraint_behavior(
    *,
    constraint: Mapping[str, object],
    established_behaviors: Mapping[str, Mapping[str, object]],
) -> ConstraintBehaviorClassification:
    """
    Classify one governed constraint against established behavior patterns.

    If no established behavior matches the governed violation kind, identify
    a new candidate behavior and stop it for governance rather than forcing
    it into an existing pattern.
    """
    constraint_id = str(constraint["constraint_id"])
    violation_kind = str(constraint.get("violation_kind", ""))

    for behavior_id, behavior in established_behaviors.items():
        if str(behavior.get("violation_kind", "")) == violation_kind:
            return ConstraintBehaviorClassification(
                constraint_id=constraint_id,
                matched_behavior_id=behavior_id,
                is_previously_unknown=False,
                proposed_behavior_id=None,
                requires_governance=False,
                eligible_for_repeated_implementation=True,
            )

    proposed_behavior_id = None
    if violation_kind == "ComparisonFailure":
        proposed_behavior_id = "Comparison"

    return ConstraintBehaviorClassification(
        constraint_id=constraint_id,
        matched_behavior_id=None,
        is_previously_unknown=True,
        proposed_behavior_id=proposed_behavior_id,
        requires_governance=True,
        eligible_for_repeated_implementation=False,
    )


__all__ = [
    "ConstraintBehaviorClassification",
    "classify_constraint_behavior",
]
