"""IT-34R3S1 — represent only constraint-construction activity in a construction run."""

from __future__ import annotations

from importlib import import_module


def _load_construction_activity_classifier():
    """Load the production construction-run boundary behavior after the RED test exists."""
    try:
        module = import_module("app.services.constraint_construction_run")
    except ModuleNotFoundError:
        return None

    return getattr(module, "classify_construction_run_activity", None)


def test_it_34_r3_s1_represents_only_constraint_construction_activity() -> None:
    """
    Feature: Define and persist governed constraint-construction run knowledge

    Rule: Separate construction-run knowledge from validation-run knowledge

    Scenario: Represent only constraint-construction activity in a construction run
    """
    classify_construction_run_activity = _load_construction_activity_classifier()

    assert classify_construction_run_activity is not None, (
        "IT-34R3S1 requires "
        "app.services.constraint_construction_run."
        "classify_construction_run_activity"
    )

    construction_stages = [
        "normalized-constraint-representation",
        "logical-schema-binding",
        "context-resolution",
        "validation-behavior",
        "instance-rdf-binding",
        "shacl-representation",
        "finding-definition",
    ]

    for stage in construction_stages:
        classification = classify_construction_run_activity(stage=stage)

        assert classification.stage == stage
        assert classification.run_type == "constraint-construction"
        assert classification.allowed_in_construction_run is True

    validation_execution_stages = [
        "received-file-validation",
        "shacl-validation-result",
        "governed-validation-finding",
    ]

    for stage in validation_execution_stages:
        classification = classify_construction_run_activity(stage=stage)

        assert classification.stage == stage
        assert classification.run_type == "validation-execution"
        assert classification.allowed_in_construction_run is False
