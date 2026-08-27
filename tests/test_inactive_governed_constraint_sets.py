"""Acceptance tests for IT-24R1S3 governed-set applicability."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from importlib import import_module
from inspect import signature
from typing import Any

import pytest


CONSTRAINT_COMPOSITION_MODULE = (
    "app.services.constraint_set_composition"
)
COMPOSITION_DATE = date(2026, 8, 26)


@dataclass(frozen=True)
class GovernedConstraintSet:
    constraint_set_id: str
    authority: str
    is_active: bool = True
    effective_from: date = date(2026, 1, 1)
    effective_through: date | None = None
    applies_to_validation_cycle: bool = True


def _composition_contract() -> Any:
    """Load the effective-set composer required by IT-24R1S3."""

    try:
        module = import_module(CONSTRAINT_COMPOSITION_MODULE)
    except ModuleNotFoundError as error:
        if error.name != CONSTRAINT_COMPOSITION_MODULE:
            raise
        pytest.fail(
            "IT-24R1S3 requires app.services.constraint_set_composition "
            "before set applicability can become green.",
            pytrace=False,
        )

    compose = getattr(module, "compose_effective_constraint_sets", None)
    assert callable(compose), (
        "IT-24R1S3 requires compose_effective_constraint_sets(...)."
    )
    assert "as_of" in signature(compose).parameters, (
        "IT-24R1S3 requires compose_effective_constraint_sets(...) to "
        "accept as_of for effective-date evaluation."
    )
    return compose


def _excluded_constraint_set(
    set_condition: str,
) -> GovernedConstraintSet:
    defaults: dict[str, object] = {
        "constraint_set_id": f"{set_condition}-overlay",
        "authority": "lender",
    }
    condition_values: dict[str, dict[str, object]] = {
        "inactive": {"is_active": False},
        "expired": {"effective_through": date(2026, 8, 25)},
        "not-yet-effective": {
            "effective_from": date(2026, 8, 27)
        },
        "inapplicable": {"applies_to_validation_cycle": False},
    }
    return GovernedConstraintSet(
        **defaults,
        **condition_values[set_condition],
    )


@pytest.mark.parametrize(
    "set_condition",
    [
        "inactive",
        "expired",
        "not-yet-effective",
        "inapplicable",
    ],
    ids=[
        "inactive",
        "expired",
        "not-yet-effective",
        "inapplicable-to-validation-cycle",
    ],
)
def test_it_24_r1_s3_excludes_a_set_that_is_not_active_and_applicable(
    set_condition: str,
) -> None:
    """Exclude each governed set that fails an applicability condition."""

    compose = _composition_contract()
    selected_gse_set = GovernedConstraintSet(
        constraint_set_id="shared-uad36",
        authority="gse",
    )
    applicable_overlay = GovernedConstraintSet(
        constraint_set_id="applicable-lender-overlay",
        authority="lender",
    )
    excluded_overlay = _excluded_constraint_set(set_condition)
    governed_overlays = (applicable_overlay, excluded_overlay)
    original_overlays = governed_overlays

    effective_constraint_sets = compose(
        (selected_gse_set,),
        governed_overlays,
        as_of=COMPOSITION_DATE,
    )

    assert effective_constraint_sets == (
        selected_gse_set,
        applicable_overlay,
    )
    assert excluded_overlay not in effective_constraint_sets
    assert governed_overlays == original_overlays
