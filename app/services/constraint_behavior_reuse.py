"""Reuse established constraint behavior across governed constraints."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping


@dataclass(frozen=True)
class BehaviorReuseResult:
    """Result of reusing one established behavior pattern."""

    behavior_id: str
    implementation_pattern: Mapping[str, object]
    instances: list[dict[str, object]]
    implementation_bindings: list[dict[str, str]]


def reuse_established_behavior(
    *,
    established_behavior: Mapping[str, object],
    constraints: Iterable[Mapping[str, object]],
) -> BehaviorReuseResult:
    """
    Reuse an established implementation pattern for multiple constraints.

    Each constraint keeps its own governed knowledge while being bound to the
    shared behavior pattern.
    """
    behavior_id = str(established_behavior["behavior_id"])
    implementation_pattern = dict(
        established_behavior["implementation_pattern"]
    )

    instances = [dict(constraint) for constraint in constraints]

    implementation_bindings = [
        {
            "constraint_id": str(instance["constraint_id"]),
            "behavior_id": behavior_id,
        }
        for instance in instances
    ]

    return BehaviorReuseResult(
        behavior_id=behavior_id,
        implementation_pattern=implementation_pattern,
        instances=instances,
        implementation_bindings=implementation_bindings,
    )


__all__ = [
    "BehaviorReuseResult",
    "reuse_established_behavior",
]
