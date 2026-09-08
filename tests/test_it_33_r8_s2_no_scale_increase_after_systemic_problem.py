"""IT-33R8S2 — do not increase scale when a batch exposes systemic problems."""

from __future__ import annotations

from importlib import import_module


def _load_batch_scaling_service():
    """Load the production batch-scaling service."""
    try:
        module = import_module("app.services.constraint_batch_scaling")
    except ModuleNotFoundError:
        return None

    return getattr(module, "next_batch_size", None)


def test_it_33_r8_s2_does_not_increase_scale_after_systemic_failure() -> None:
    """
    Feature: Build governed validation constraints at scale

    Rule: Scale constraint-production batches logarithmically as confidence grows

    Scenario: Do not increase scale when the current batch exposes systemic problems
    """
    next_batch_size = _load_batch_scaling_service()

    assert next_batch_size is not None, (
        "IT-33R8S2 requires "
        "app.services.constraint_batch_scaling.next_batch_size"
    )

    result = next_batch_size(
        current_batch_size=64,
        current_batch_completed_successfully=False,
        regression_suite_green=False,
        systemic_failure=True,
        remaining_constraints=603,
    )

    # A systemic problem prevents logarithmic growth.
    assert result.current_batch_size == 64
    assert result.proposed_batch_size == 64
    assert result.may_scale is False

    # The decision explicitly identifies the systemic problem as the reason.
    assert result.reason == (
        "systemic failure detected; resolve the production process "
        "before increasing batch size"
    )
