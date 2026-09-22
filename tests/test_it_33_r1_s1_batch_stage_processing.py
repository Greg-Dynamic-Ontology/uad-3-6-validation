"""IT-33R1S1 — process a bounded batch at one construction stage."""

from __future__ import annotations

from importlib import import_module


def _load_batch_processor():
    """Load the production batch-stage processor after the RED test exists."""
    try:
        module = import_module("app.services.constraint_batch_processor")
    except ModuleNotFoundError:
        return None

    return getattr(module, "process_constraint_batch_stage", None)


def test_it_33_r1_s1_processes_each_eligible_constraint_without_stopping_on_exception() -> None:
    """
    Feature: Build governed validation constraints at scale

    Rule: Process governed constraints in bounded batches through each
    construction stage before advancing the batch

    Scenario: Process a batch at a constraint-construction stage
    """
    process_constraint_batch_stage = _load_batch_processor()

    assert process_constraint_batch_stage is not None, (
        "IT-33R1S1 requires "
        "app.services.constraint_batch_processor."
        "process_constraint_batch_stage"
    )

    constraints = [
        {"otdd_id": "IT-33R1C1", "eligible": True},
        {"otdd_id": "IT-33R1C2", "eligible": True},
        {"otdd_id": "IT-33R1C3", "eligible": True},
        {"otdd_id": "IT-33R1C4", "eligible": False},
    ]

    attempted: list[str] = []

    def execute_stage(constraint: dict[str, object]) -> None:
        constraint_id = str(constraint["otdd_id"])
        attempted.append(constraint_id)

        if constraint_id == "IT-33R1C2":
            raise ValueError("unresolved governed source identity")

    result = process_constraint_batch_stage(
        constraints=constraints,
        stage_name="normalized-constraint-representation",
        execute_stage=execute_stage,
    )

    # Every eligible constraint is processed at this stage.
    assert attempted == [
        "IT-33R1C1",
        "IT-33R1C2",
        "IT-33R1C3",
    ]

    # Every successfully processed constraint becomes eligible for verification.
    assert result.verification_eligible_ids == [
        "IT-33R1C1",
        "IT-33R1C3",
    ]

    # A constraint that cannot be processed is identified as an exception.
    assert len(result.exceptions) == 1
    exception = result.exceptions[0]
    assert exception.constraint_id == "IT-33R1C2"
    assert exception.stage_name == "normalized-constraint-representation"
    assert exception.reason == "unresolved governed source identity"

    # The exception does not prevent later eligible constraints from processing.
    assert "IT-33R1C3" in result.processed_ids

    # Ineligible constraints are not processed at this stage.
    assert "IT-33R1C4" not in attempted
    assert "IT-33R1C4" not in result.processed_ids
