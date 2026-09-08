"""Scale OTDD constraint-production batches as confidence grows."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BatchScalingDecision:
    """Decision about whether and how much the next batch may scale."""

    current_batch_size: int
    proposed_batch_size: int
    may_scale: bool
    reason: str


def next_batch_size(
    *,
    current_batch_size: int,
    current_batch_completed_successfully: bool,
    regression_suite_green: bool,
    systemic_failure: bool,
    remaining_constraints: int,
) -> BatchScalingDecision:
    """
    Propose the next logarithmically scaled batch size.

    A successful batch with a green regression suite and no systemic failure
    earns a doubling of the current batch size, capped by the remaining
    constraint population.

    A systemic failure explicitly blocks scaling until the production process
    is corrected.
    """
    if current_batch_size < 1:
        raise ValueError("current_batch_size must be at least 1")

    if remaining_constraints < 0:
        raise ValueError("remaining_constraints cannot be negative")

    if systemic_failure:
        return BatchScalingDecision(
            current_batch_size=current_batch_size,
            proposed_batch_size=current_batch_size,
            may_scale=False,
            reason=(
                "systemic failure detected; resolve the production process "
                "before increasing batch size"
            ),
        )

    may_scale = (
        current_batch_completed_successfully
        and regression_suite_green
    )

    if may_scale:
        proposed_batch_size = min(
            current_batch_size * 2,
            remaining_constraints,
        )
        reason = (
            "current batch completed successfully, regression suite is green, "
            "and no systemic failure was detected"
        )
    else:
        proposed_batch_size = current_batch_size
        reason = "current batch has not earned a larger scale"

    return BatchScalingDecision(
        current_batch_size=current_batch_size,
        proposed_batch_size=proposed_batch_size,
        may_scale=may_scale,
        reason=reason,
    )


__all__ = [
    "BatchScalingDecision",
    "next_batch_size",
]