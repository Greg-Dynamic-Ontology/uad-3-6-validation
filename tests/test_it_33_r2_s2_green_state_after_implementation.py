"""IT-33R2S2 — establish a GREEN state after implementation."""

from __future__ import annotations

from importlib import import_module


def _load_green_state_service():
    """Load the production GREEN-state service after the RED test exists."""
    try:
        module = import_module("app.services.otdd_green_state")
    except ModuleNotFoundError:
        return None

    return getattr(module, "establish_green_state", None)


def test_it_33_r2_s2_establishes_green_state_after_implementation() -> None:
    """
    Feature: Build governed validation constraints at scale

    Rule: Prove expected behavior before generating the artifact that satisfies it

    Scenario: Establish a GREEN state after implementation
    """
    establish_green_state = _load_green_state_service()

    assert establish_green_state is not None, (
        "IT-33R2S2 requires "
        "app.services.otdd_green_state.establish_green_state"
    )

    events: list[str] = []
    artifact_exists = False

    def generate_artifact() -> None:
        nonlocal artifact_exists
        events.append("artifact-generated")
        artifact_exists = True

    def execute_tests():
        events.append("tests-executed")

        assert artifact_exists is True

        return {
            "passed": True,
            "verified_behavior": (
                "normalized governed constraint representation exists "
                "and preserves governed identity"
            ),
        }

    result = establish_green_state(
        constraint_id="IT-33R2C1",
        stage_name="normalized-constraint-representation",
        expected_behavior=(
            "normalized governed constraint representation exists "
            "and preserves governed identity"
        ),
        generate_artifact=generate_artifact,
        execute_tests=execute_tests,
        artifact_exists=lambda: artifact_exists,
    )

    # Implementation is generated before verification is executed.
    assert events == [
        "artifact-generated",
        "tests-executed",
    ]

    # The required artifact exists after implementation.
    assert result.artifact_exists_after_implementation is True

    # The stage tests now pass.
    assert result.is_green is True

    # GREEN verifies the same behavior that was established in RED.
    assert result.verified_behavior == (
        "normalized governed constraint representation exists "
        "and preserves governed identity"
    )

    # A GREEN constraint is eligible to advance to the next construction stage.
    assert result.eligible_for_next_stage is True
