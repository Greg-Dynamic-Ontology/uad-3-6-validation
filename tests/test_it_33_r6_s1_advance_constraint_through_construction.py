"""IT-33R6S1 — advance a constraint through the construction process."""

from __future__ import annotations

from importlib import import_module


def _load_construction_process_service():
    """Load the production construction-process service after RED exists."""
    try:
        module = import_module("app.services.constraint_construction_process")
    except ModuleNotFoundError:
        return None

    return getattr(module, "advance_constraint_through_construction", None)


def test_it_33_r6_s1_advances_constraint_through_required_construction_stages() -> None:
    """
    Feature: Build governed validation constraints at scale

    Rule: Complete each governed constraint through the required OTDD
    knowledge-construction stages

    Scenario: Advance a constraint through the construction process
    """
    advance_constraint_through_construction = (
        _load_construction_process_service()
    )

    assert advance_constraint_through_construction is not None, (
        "IT-33R6S1 requires "
        "app.services.constraint_construction_process."
        "advance_constraint_through_construction"
    )

    required_stages = [
        "normalized-constraint-representation",
        "logical-schema-binding",
        "context-resolution",
        "validation-behavior",
        "instance-rdf-binding",
        "shacl-representation",
        "governed-validation-finding",
    ]

    completed_stages: list[str] = []

    def execute_stage(stage_name: str) -> dict[str, object]:
        completed_stages.append(stage_name)
        return {
            "stage_name": stage_name,
            "verified": True,
        }

    result = advance_constraint_through_construction(
        constraint_id=(
            "https://dynamicontology.com/uad36/constraint/0100.0007"
        ),
        required_stages=required_stages,
        execute_stage=execute_stage,
    )

    # The constraint advances through every required stage in order.
    assert completed_stages == required_stages

    # Every required stage is recorded as verified.
    assert result.verified_stages == required_stages

    # The governed constraint identity remains associated with the process.
    assert (
        result.constraint_id
        == "https://dynamicontology.com/uad36/constraint/0100.0007"
    )

    # A constraint is complete only after every required stage is verified.
    assert result.is_complete is True
    assert result.next_stage is None
