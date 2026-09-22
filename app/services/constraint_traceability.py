"""Preserve traceability across governed constraint representations."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ConstraintTraceability:
    """Traceability relationships preserved during constraint construction."""

    governed_source_identity: str
    normalized_constraint_identity: str
    source_provenance: str
    executable_representation_identity: str
    executable_representation_of: str


def build_constraint_traceability(
    *,
    governed_source_identity: str,
    normalized_constraint_identity: str,
    source_provenance: str,
    executable_representation_identity: str,
) -> ConstraintTraceability:
    """
    Build the traceability record required by IT-33R3S1.

    The generated executable representation is explicitly linked back to
    the normalized governed constraint while preserving source identity
    and provenance.
    """
    return ConstraintTraceability(
        governed_source_identity=governed_source_identity,
        normalized_constraint_identity=normalized_constraint_identity,
        source_provenance=source_provenance,
        executable_representation_identity=(
            executable_representation_identity
        ),
        executable_representation_of=normalized_constraint_identity,
    )


__all__ = [
    "ConstraintTraceability",
    "build_constraint_traceability",
]
