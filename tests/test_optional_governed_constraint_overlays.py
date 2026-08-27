"""Acceptance tests for IT-24R1S2 optional governed overlays."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from typing import Any

import pytest


CONSTRAINT_COMPOSITION_MODULE = (
    "app.services.constraint_set_composition"
)


@dataclass(frozen=True)
class GovernedConstraintSet:
    constraint_set_id: str
    authority: str
    constraint_ids: frozenset[str]


def _composition_contract() -> Any:
    """Load the constraint-set composer required by IT-24R1S2."""

    try:
        module = import_module(CONSTRAINT_COMPOSITION_MODULE)
    except ModuleNotFoundError as error:
        if error.name != CONSTRAINT_COMPOSITION_MODULE:
            raise
        pytest.fail(
            "IT-24R1S2 requires app.services.constraint_set_composition "
            "before governed overlays can become green.",
            pytrace=False,
        )

    compose = getattr(module, "compose_effective_constraint_sets", None)
    assert callable(compose), (
        "IT-24R1S2 requires compose_effective_constraint_sets("
        "selected_gse_constraint_sets, governed_overlays)."
    )
    return compose


def _selected_gse_constraint_sets(
) -> tuple[GovernedConstraintSet, ...]:
    return (
        GovernedConstraintSet(
            constraint_set_id="shared-uad36",
            authority="gse",
            constraint_ids=frozenset({"UAD-SHARED-001"}),
        ),
        GovernedConstraintSet(
            constraint_set_id="fannie-mae-uad36",
            authority="fannie_mae",
            constraint_ids=frozenset({"UAD-FANNIE-001"}),
        ),
    )


def _governed_overlays(count: int) -> tuple[GovernedConstraintSet, ...]:
    overlays = (
        GovernedConstraintSet(
            constraint_set_id="lender-1-overlay",
            authority="lender",
            constraint_ids=frozenset({"LENDER-001"}),
        ),
        GovernedConstraintSet(
            constraint_set_id="amc-1-overlay",
            authority="amc",
            constraint_ids=frozenset({"AMC-001"}),
        ),
        GovernedConstraintSet(
            constraint_set_id="investor-1-overlay",
            authority="other",
            constraint_ids=frozenset({"INVESTOR-001"}),
        ),
    )
    return overlays[:count]


@pytest.mark.parametrize(
    "overlay_count",
    [0, 1, 3],
    ids=["no-overlays", "one-overlay", "multiple-overlays"],
)
def test_it_24_r1_s2_composes_optional_governed_overlays_with_gse_sets(
    overlay_count: int,
) -> None:
    """Union selected GSE sets with zero or more governed overlays."""

    compose = _composition_contract()
    selected_gse_constraint_sets = _selected_gse_constraint_sets()
    governed_overlays = _governed_overlays(overlay_count)
    original_gse_sets = selected_gse_constraint_sets
    original_overlays = governed_overlays

    effective_constraint_sets = compose(
        selected_gse_constraint_sets,
        governed_overlays,
    )

    assert effective_constraint_sets == (
        *selected_gse_constraint_sets,
        *governed_overlays,
    )
    assert selected_gse_constraint_sets == original_gse_sets
    assert governed_overlays == original_overlays
