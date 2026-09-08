"""IT-33R4S1 — reuse an established constraint behavior."""

from __future__ import annotations

from importlib import import_module


def _load_behavior_reuse_service():
    """Load the production behavior-reuse service after the RED test exists."""
    try:
        module = import_module("app.services.constraint_behavior_reuse")
    except ModuleNotFoundError:
        return None

    return getattr(module, "reuse_established_behavior", None)


def test_it_33_r4_s1_reuses_established_constraint_behavior() -> None:
    """
    Feature: Build governed validation constraints at scale

    Rule: Classify recurring constraint behavior before generating repeated implementations

    Scenario: Reuse an established constraint behavior
    """
    reuse_established_behavior = _load_behavior_reuse_service()

    assert reuse_established_behavior is not None, (
        "IT-33R4S1 requires "
        "app.services.constraint_behavior_reuse."
        "reuse_established_behavior"
    )

    established_behavior = {
        "behavior_id": "RequiredPresence",
        "implementation_pattern": {
            "technology": "SHACL",
            "constraint_component": "sh:MinCountConstraintComponent",
            "minimum_count": 1,
        },
    }

    constraints = [
        {
            "constraint_id": (
                "https://dynamicontology.com/uad36/constraint/0100.0007"
            ),
            "data_point": "AddressLineText",
            "context": "subject-property-address",
        },
        {
            "constraint_id": (
                "https://dynamicontology.com/uad36/constraint/0100.0008"
            ),
            "data_point": "CityName",
            "context": "subject-property-address",
        },
    ]

    result = reuse_established_behavior(
        established_behavior=established_behavior,
        constraints=constraints,
    )

    # The established behavior pattern is reused.
    assert result.behavior_id == "RequiredPresence"
    assert result.implementation_pattern == {
        "technology": "SHACL",
        "constraint_component": "sh:MinCountConstraintComponent",
        "minimum_count": 1,
    }

    # Each governed constraint supplies its own constraint-specific knowledge.
    assert result.instances == [
        {
            "constraint_id": (
                "https://dynamicontology.com/uad36/constraint/0100.0007"
            ),
            "data_point": "AddressLineText",
            "context": "subject-property-address",
        },
        {
            "constraint_id": (
                "https://dynamicontology.com/uad36/constraint/0100.0008"
            ),
            "data_point": "CityName",
            "context": "subject-property-address",
        },
    ]

    # Each generated implementation remains traceable to its governed constraint.
    assert result.implementation_bindings == [
        {
            "constraint_id": (
                "https://dynamicontology.com/uad36/constraint/0100.0007"
            ),
            "behavior_id": "RequiredPresence",
        },
        {
            "constraint_id": (
                "https://dynamicontology.com/uad36/constraint/0100.0008"
            ),
            "behavior_id": "RequiredPresence",
        },
    ]

