"""IT-33R5S2 — resume construction after an exception is resolved."""

from __future__ import annotations

from importlib import import_module


def _load_exception_resume_service():
    """Load the production exception-resume service after RED exists."""
    try:
        module = import_module("app.services.constraint_exception_resume")
    except ModuleNotFoundError:
        return None

    return getattr(module, "resume_resolved_constraint", None)


def test_it_33_r5_s2_resumes_construction_from_unresolved_stage() -> None:
    """
    Feature: Build governed validation constraints at scale

    Rule: Isolate exceptions without stopping production of understood constraints

    Scenario: Resume construction after an exception is resolved
    """
    resume_resolved_constraint = _load_exception_resume_service()

    assert resume_resolved_constraint is not None, (
        "IT-33R5S2 requires "
        "app.services.constraint_exception_resume."
        "resume_resolved_constraint"
    )

    exception_record = {
        "constraint_id": (
            "https://dynamicontology.com/uad36/constraint/0100.0099"
        ),
        "otdd_id": "IT-33R5C1",
        "stage_name": "constraint-behavior-classification",
        "reason": "previously unknown constraint behavior",
        "status": "exception",
    }

    previously_verified_stages = [
        "normalized-constraint-representation",
        "logical-schema-binding",
        "context-resolution",
    ]

    result = resume_resolved_constraint(
        exception_record=exception_record,
        resolution={
            "behavior_id": "Comparison",
            "governance_status": "approved",
        },
        previously_verified_stages=previously_verified_stages,
    )

    # Processing resumes from the stage that was unresolved.
    assert result.resume_stage == "constraint-behavior-classification"

    # The resolved constraint becomes eligible for automated production again.
    assert result.status == "resolved"
    assert result.requires_review is False
    assert result.eligible_for_automated_production is True

    # Previously verified stages remain verified and are not reconstructed.
    assert result.preserved_verified_stages == previously_verified_stages

    # The resolution knowledge is retained for the resumed stage.
    assert result.resolution == {
        "behavior_id": "Comparison",
        "governance_status": "approved",
    }
