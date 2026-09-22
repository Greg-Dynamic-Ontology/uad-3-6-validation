"""Establish the OTDD GREEN state after implementation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


GenerateArtifact = Callable[[], None]
ExecuteTests = Callable[[], dict[str, object]]
ArtifactExists = Callable[[], bool]


@dataclass(frozen=True)
class GreenStateResult:
    """Outcome of proving expected behavior after implementation."""

    constraint_id: str
    stage_name: str
    artifact_exists_after_implementation: bool
    is_green: bool
    verified_behavior: str
    eligible_for_next_stage: bool


def establish_green_state(
    *,
    constraint_id: str,
    stage_name: str,
    expected_behavior: str,
    generate_artifact: GenerateArtifact,
    execute_tests: ExecuteTests,
    artifact_exists: ArtifactExists,
) -> GreenStateResult:
    """
    Generate the required artifact, execute the stage tests, and prove GREEN.

    A valid GREEN state requires:
    - the required artifact to exist after generation;
    - the stage tests to pass; and
    - the verified behavior to match the behavior established during RED.
    """
    generate_artifact()

    artifact_exists_after_implementation = artifact_exists()
    if not artifact_exists_after_implementation:
        raise ValueError(
            "Cannot establish GREEN state because the required artifact "
            "does not exist after implementation."
        )

    test_result = execute_tests()

    passed = bool(test_result.get("passed", False))
    verified_behavior = str(test_result.get("verified_behavior", ""))

    if not passed:
        raise ValueError(
            "Cannot establish GREEN state because the stage tests failed."
        )

    if not verified_behavior:
        raise ValueError(
            "GREEN state must record the behavior verified by the passing tests."
        )

    if verified_behavior != expected_behavior:
        raise ValueError(
            "GREEN state verified behavior does not match the behavior "
            "established during RED."
        )

    return GreenStateResult(
        constraint_id=constraint_id,
        stage_name=stage_name,
        artifact_exists_after_implementation=True,
        is_green=True,
        verified_behavior=verified_behavior,
        eligible_for_next_stage=True,
    )


__all__ = [
    "GreenStateResult",
    "establish_green_state",
]
