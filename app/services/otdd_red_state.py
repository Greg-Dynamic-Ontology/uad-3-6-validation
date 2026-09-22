"""Establish the OTDD RED state for one construction stage."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence


GenerateTests = Callable[[], Sequence[str]]
ExecuteTests = Callable[[Sequence[str]], dict[str, object]]
ArtifactExists = Callable[[], bool]


@dataclass(frozen=True)
class RedStateResult:
    """Outcome of proving expected behavior before implementation."""

    constraint_id: str
    stage_name: str
    artifact_existed_before_test: bool
    is_red: bool
    failure_kind: str
    expected_behavior: str


def establish_red_state(
    *,
    constraint_id: str,
    stage_name: str,
    generate_tests: GenerateTests,
    execute_tests: ExecuteTests,
    artifact_exists: ArtifactExists,
) -> RedStateResult:
    """
    Generate and execute stage tests before implementation exists.

    A valid RED state requires:
    - the required artifact to be absent before test execution;
    - the generated tests to fail; and
    - the failure to record the expected future behavior.
    """
    artifact_existed_before_test = artifact_exists()
    if artifact_existed_before_test:
        raise ValueError(
            "Cannot establish RED state after the required artifact exists."
        )

    test_ids = list(generate_tests())
    if not test_ids:
        raise ValueError(
            "Cannot establish RED state without generated executable tests."
        )

    test_result = execute_tests(test_ids)

    passed = bool(test_result.get("passed", False))
    failure_kind = str(test_result.get("failure_kind", ""))
    expected_behavior = str(test_result.get("expected_behavior", ""))

    if passed:
        raise ValueError(
            "Expected RED state, but generated tests passed before implementation."
        )

    if not failure_kind:
        raise ValueError(
            "RED state must identify why the generated tests failed."
        )

    if not expected_behavior:
        raise ValueError(
            "RED state must record the behavior the implementation must satisfy."
        )

    return RedStateResult(
        constraint_id=constraint_id,
        stage_name=stage_name,
        artifact_existed_before_test=artifact_existed_before_test,
        is_red=True,
        failure_kind=failure_kind,
        expected_behavior=expected_behavior,
    )


__all__ = [
    "RedStateResult",
    "establish_red_state",
]
