"""Acceptance test for IT-24R1S6 canonical-identity deduplication."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from typing import Any

import pytest


CONSTRAINT_COMPOSITION_MODULE = (
    "app.services.constraint_set_composition"
)


@dataclass(frozen=True)
class GovernedConstraint:
    canonical_constraint_id: str
    source_authority: str
    requirement_key: str
    required_value: str


def _deduplication_contract() -> Any:
    """Load the canonical deduplicator required by IT-24R1S6."""

    try:
        module = import_module(CONSTRAINT_COMPOSITION_MODULE)
    except ModuleNotFoundError as error:
        if error.name != CONSTRAINT_COMPOSITION_MODULE:
            raise
        pytest.fail(
            "IT-24R1S6 requires app.services.constraint_set_composition "
            "before canonical deduplication can become green.",
            pytrace=False,
        )

    deduplicate = getattr(
        module,
        "deduplicate_constraints_by_canonical_identity",
        None,
    )
    assert callable(deduplicate), (
        "IT-24R1S6 requires "
        "deduplicate_constraints_by_canonical_identity(constraints)."
    )
    return deduplicate


def test_it_24_r1_s6_deduplicates_only_by_canonical_identity() -> None:
    """Merge shared identity occurrences but retain equivalent identities."""

    deduplicate = _deduplication_contract()
    shared_fannie_occurrence = GovernedConstraint(
        canonical_constraint_id="UAD-CANONICAL-001",
        source_authority="fannie_mae",
        requirement_key="subject.occupancy_type",
        required_value="owner_occupied",
    )
    shared_freddie_occurrence = GovernedConstraint(
        canonical_constraint_id="UAD-CANONICAL-001",
        source_authority="freddie_mac",
        requirement_key="subject.occupancy_type",
        required_value="owner_occupied",
    )
    equivalent_lender_constraint = GovernedConstraint(
        canonical_constraint_id="LENDER-CANONICAL-901",
        source_authority="lender",
        requirement_key="subject.occupancy_type",
        required_value="owner_occupied",
    )
    constraints = (
        shared_fannie_occurrence,
        shared_freddie_occurrence,
        equivalent_lender_constraint,
    )

    effective_constraints = deduplicate(constraints)

    assert effective_constraints == (
        shared_fannie_occurrence,
        equivalent_lender_constraint,
    )
    assert tuple(
        constraint.canonical_constraint_id
        for constraint in effective_constraints
    ) == (
        "UAD-CANONICAL-001",
        "LENDER-CANONICAL-901",
    )
    assert constraints == (
        shared_fannie_occurrence,
        shared_freddie_occurrence,
        equivalent_lender_constraint,
    )
