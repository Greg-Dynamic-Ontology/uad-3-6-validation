"""IT-33R2S1 — establish a RED state before implementation."""

from __future__ import annotations

from importlib import import_module


def _load_red_state_service():
    """Load the production RED-state service after the RED test exists."""
    try:
        module = import_module("app.services.otdd_red_state")
    except ModuleNotFoundError:
        return None

    return getattr(module, "establish_red_state", None)


def test_it_33_r2_s1_establishes_red_state_before_artifact_generation() -> None:
    """
    Feature: Build governed validation constraints at scale

    Rule: Prove expected behavior before generating the artifact that satisfies it

    Scenario: Establish a RED state before implementation
    """
    establish_red_state = _load_red_state_service()

    assert establish_red_state is not None, (
        "IT-33R2S1 requires "
        "app.services.otdd_red_state.establish_red_state"
    )

    events: list[str] = []
    artifact_exists = False

    def generate_tests() -> list[str]:
        events.append("tests-generated")
        return [
            "test_normalized_constraint_exists",
            "test_normalized_constraint_preserves_identity",
        ]

    def execute_tests(test_ids: list[str]):
        events.append("tests-executed")

        assert artifact_exists is False
        assert test_ids == [
            "test_normalized_constraint_exists",
            "test_normalized_constraint_preserves_identity",
        ]

        return {
            "passed": False,
            "failure_kind": "missing-required-artifact",
            "expected_behavior": (
                "normalized governed constraint representation exists "
                "and preserves governed identity"
            ),
        }

    result = establish_red_state(
        constraint_id="IT-33R2C1",
        stage_name="normalized-constraint-representation",
        generate_tests=generate_tests,
        execute_tests=execute_tests,
        artifact_exists=lambda: artifact_exists,
    )

    # Tests are generated before they are executed.
    assert events == [
        "tests-generated",
        "tests-executed",
    ]

    # The required artifact does not exist before the RED proof.
    assert result.artifact_existed_before_test is False

    # The generated executable tests fail before implementation.
    assert result.is_red is True
    assert result.failure_kind == "missing-required-artifact"

    # The RED result records the behavior the future artifact must satisfy.
    assert result.expected_behavior == (
        "normalized governed constraint representation exists "
        "and preserves governed identity"
    )

    # A RED state must not generate the implementation artifact.
    assert artifact_exists is False
