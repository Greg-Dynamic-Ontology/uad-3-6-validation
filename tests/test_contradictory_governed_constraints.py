"""Acceptance test for IT-24R1S5 contradictory governed constraints."""

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
    constraint_id: str
    requirement_key: str
    required_value: str


@dataclass(frozen=True)
class GovernedConstraintSet:
    constraint_set_id: str
    authority: str
    constraints: tuple[GovernedConstraint, ...]


def _composition_contract() -> tuple[Any, type[Exception]]:
    """Load the contradiction contract required by IT-24R1S5."""

    try:
        module = import_module(CONSTRAINT_COMPOSITION_MODULE)
    except ModuleNotFoundError as error:
        if error.name != CONSTRAINT_COMPOSITION_MODULE:
            raise
        pytest.fail(
            "IT-24R1S5 requires app.services.constraint_set_composition "
            "before contradiction rejection can become green.",
            pytrace=False,
        )

    compose = getattr(module, "compose_effective_constraint_sets", None)
    contradiction_error = getattr(
        module,
        "ContradictoryGovernedConstraintsError",
        None,
    )
    assert callable(compose), (
        "IT-24R1S5 requires compose_effective_constraint_sets(...)."
    )
    assert isinstance(contradiction_error, type) and issubclass(
        contradiction_error,
        Exception,
    ), "IT-24R1S5 requires ContradictoryGovernedConstraintsError."
    return compose, contradiction_error


def test_it_24_r1_s5_rejects_contradictory_active_constraints() -> None:
    """Reject conflicting requirements instead of choosing precedence."""

    compose, contradiction_error = _composition_contract()
    gse_constraint_set = GovernedConstraintSet(
        constraint_set_id="shared-uad36",
        authority="gse",
        constraints=(
            GovernedConstraint(
                constraint_id="UAD-GSE-001",
                requirement_key="subject.property_structure_type",
                required_value="detached",
            ),
        ),
    )
    lender_overlay = GovernedConstraintSet(
        constraint_set_id="lender-1-overlay",
        authority="lender",
        constraints=(
            GovernedConstraint(
                constraint_id="LENDER-001",
                requirement_key="subject.property_structure_type",
                required_value="attached",
            ),
        ),
    )
    original_gse_constraint_set = gse_constraint_set
    original_lender_overlay = lender_overlay

    with pytest.raises(contradiction_error):
        compose((gse_constraint_set,), (lender_overlay,))

    assert gse_constraint_set == original_gse_constraint_set
    assert lender_overlay == original_lender_overlay
