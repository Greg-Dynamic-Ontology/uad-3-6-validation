"""IT-33R8S1 — increase batch size after successful processing."""

from __future__ import annotations

from importlib import import_module


def _load_batch_scaling_service():
    """Load the production batch-scaling service after RED exists."""
    try:
        module = import_module("app.services.constraint_batch_scaling")
    except ModuleNotFoundError:
        return None

    return getattr(module, "next_batch_size", None)


def test_it_33_r8_s1_increases_batch_size_after_successful_processing() -> None:
    """
    Feature: Build governed validation constraints at scale

    Rule: Scale constraint-production batches logarithmically as confidence grows

    Scenario: Increase the batch size after successful processing
    """
    next_batch_size = _load_batch_scaling_service()

    assert next_batch_size is not None, (
        "IT-33R8S1 requires "
        "app.services.constraint_batch_scaling.next_batch_size"
    )

    result = next_batch_size(
        current_batch_size=32,
        current_batch_completed_successfully=True,
        regression_suite_green=True,
        systemic_failure=False,
        remaining_constraints=698,
    )

    # Successful processing earns a logarithmic increase in batch size.
    assert result.current_batch_size == 32
    assert result.proposed_batch_size == 64

    # The next batch is allowed to scale only after successful processing.
    assert result.may_scale is True

    # The scale decision records why the larger batch is permitted.
    assert result.reason == (
        "current batch completed successfully, regression suite is green, "
        "and no systemic failure was detected"
    )
