"""IT-33R4S2 — identify a previously unknown constraint behavior."""

from __future__ import annotations

from importlib import import_module


def _load_behavior_classification_service():
    """Load the production behavior-classification service after RED exists."""
    try:
        module = import_module("app.services.constraint_behavior_classification")
    except ModuleNotFoundError:
        return None

    return getattr(module, "classify_constraint_behavior", None)


def test_it_33_r4_s2_identifies_previously_unknown_constraint_behavior() -> None:
    """
    Feature: Build governed validation constraints at scale

    Rule: Classify recurring constraint behavior before generating repeated implementations

    Scenario: Identify a previously unknown constraint behavior
    """
    classify_constraint_behavior = _load_behavior_classification_service()

    assert classify_constraint_behavior is not None, (
        "IT-33R4S2 requires "
        "app.services.constraint_behavior_classification."
        "classify_constraint_behavior"
    )

    established_behaviors = {
        "RequiredPresence": {
            "violation_kind": "MissingRequiredValue",
        },
        "ProhibitedPresence": {
            "violation_kind": "ProhibitedValuePresent",
        },
    }

    constraint = {
        "constraint_id": (
            "https://dynamicontology.com/uad36/constraint/0100.0099"
        ),
        "requirement": (
            "The reported value must be greater than the comparison value."
        ),
        "violation_condition": (
            "If the reported value is less than or equal to the comparison value"
        ),
        "violation_kind": "ComparisonFailure",
    }

    result = classify_constraint_behavior(
        constraint=constraint,
        established_behaviors=established_behaviors,
    )

    # The constraint does not get forced into an established behavior.
    assert result.matched_behavior_id is None

    # The previously unknown behavior is explicitly identified.
    assert result.is_previously_unknown is True
    assert result.proposed_behavior_id == "Comparison"

    # The governed constraint remains associated with the classification.
    assert (
        result.constraint_id
        == "https://dynamicontology.com/uad36/constraint/0100.0099"
    )

    # Unknown behavior is surfaced for governance before repeated
    # implementation generation can proceed.
    assert result.requires_governance is True
    assert result.eligible_for_repeated_implementation is False
