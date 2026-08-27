"""Acceptance tests for IT-24R1S4 governed-overlay weakening."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from typing import Any

import pytest


CONSTRAINT_COMPOSITION_MODULE = (
    "app.services.constraint_set_composition"
)
GSE_GOVERNANCE_MODULE = "app.services.gse_constraint_governance"


@dataclass(frozen=True)
class GovernedConstraint:
    constraint_id: str
    severity: str


@dataclass(frozen=True)
class GovernedConstraintSet:
    constraint_set_id: str
    authority: str
    constraints: tuple[GovernedConstraint, ...] = ()
    disabled_constraint_ids: frozenset[str] = frozenset()
    severity_overrides: tuple[tuple[str, str], ...] = ()


def _composition_contract() -> tuple[Any, type[Exception]]:
    """Load the composition contract required by IT-24R1S4."""

    try:
        composition_module = import_module(CONSTRAINT_COMPOSITION_MODULE)
        governance_module = import_module(GSE_GOVERNANCE_MODULE)
    except ModuleNotFoundError as error:
        if error.name not in {
            CONSTRAINT_COMPOSITION_MODULE,
            GSE_GOVERNANCE_MODULE,
        }:
            raise
        pytest.fail(
            "IT-24R1S4 requires governed constraint composition before "
            "overlay weakening can become green.",
            pytrace=False,
        )

    compose = getattr(
        composition_module,
        "compose_effective_constraint_sets",
        None,
    )
    weakening_error = getattr(
        governance_module,
        "GovernedConstraintWeakeningError",
        None,
    )
    assert callable(compose), (
        "IT-24R1S4 requires compose_effective_constraint_sets(...)."
    )
    assert isinstance(weakening_error, type) and issubclass(
        weakening_error,
        Exception,
    ), "IT-24R1S4 requires GovernedConstraintWeakeningError."
    return compose, weakening_error


@pytest.mark.parametrize(
    ("weakening_action", "disabled_ids", "severity_overrides"),
    [
        (
            "disable",
            frozenset({"UAD-GSE-001"}),
            (),
        ),
        (
            "downgrade",
            frozenset(),
            (("UAD-GSE-001", "Warning"),),
        ),
    ],
    ids=["disable", "downgrade"],
)
def test_it_24_r1_s4_prevents_an_overlay_from_weakening_a_gse_constraint(
    weakening_action: str,
    disabled_ids: frozenset[str],
    severity_overrides: tuple[tuple[str, str], ...],
) -> None:
    """Reject disabling or downgrading an applicable GSE constraint."""

    compose, weakening_error = _composition_contract()
    gse_constraint_set = GovernedConstraintSet(
        constraint_set_id="shared-uad36",
        authority="gse",
        constraints=(
            GovernedConstraint(
                constraint_id="UAD-GSE-001",
                severity="Fatal",
            ),
        ),
    )
    original_gse_constraint_set = gse_constraint_set
    overlay = GovernedConstraintSet(
        constraint_set_id=f"lender-{weakening_action}-overlay",
        authority="lender",
        disabled_constraint_ids=disabled_ids,
        severity_overrides=severity_overrides,
    )

    with pytest.raises(weakening_error):
        compose((gse_constraint_set,), (overlay,))

    assert gse_constraint_set == original_gse_constraint_set
