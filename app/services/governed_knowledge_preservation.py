"""Preserve governed knowledge independently of implementation-specific structure."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class GovernedKnowledgePreservation:
    """Preserved governed meaning plus implementation linkage."""

    governed_constraint_identity: str
    governed_requirement: str
    executable_representation_identity: str
    executable_representation_of: str
    implementation_structure: Mapping[str, object]
    meaning_source: str


def preserve_governed_knowledge(
    *,
    governed_constraint_identity: str,
    governed_requirement: str,
    executable_representation_identity: str,
    implementation_structure: Mapping[str, object],
) -> GovernedKnowledgePreservation:
    """
    Preserve governed identity and meaning while linking an executable representation.

    The executable artifact implements the governed constraint, but its identity and
    technology-specific structure do not replace the governed constraint or become
    the source of its meaning.
    """
    return GovernedKnowledgePreservation(
        governed_constraint_identity=governed_constraint_identity,
        governed_requirement=governed_requirement,
        executable_representation_identity=(
            executable_representation_identity
        ),
        executable_representation_of=governed_constraint_identity,
        implementation_structure=dict(implementation_structure),
        meaning_source="governed-constraint",
    )


__all__ = [
    "GovernedKnowledgePreservation",
    "preserve_governed_knowledge",
]
