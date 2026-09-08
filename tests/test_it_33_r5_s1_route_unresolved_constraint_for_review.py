"""IT-33R5S1 — route an unresolved constraint for review."""

from __future__ import annotations

from importlib import import_module


def _load_exception_routing_service():
    """Load the production exception-routing service after RED exists."""
    try:
        module = import_module("app.services.constraint_exception_routing")
    except ModuleNotFoundError:
        return None

    return getattr(module, "route_unresolved_constraint", None)


def test_it_33_r5_s1_routes_unresolved_constraint_for_review() -> None:
    """
    Feature: Build governed validation constraints at scale

    Rule: Isolate exceptions without stopping production of understood constraints

    Scenario: Route an unresolved constraint for review
    """
    route_unresolved_constraint = _load_exception_routing_service()

    assert route_unresolved_constraint is not None, (
        "IT-33R5S1 requires "
        "app.services.constraint_exception_routing."
        "route_unresolved_constraint"
    )

    constraint = {
        "constraint_id": (
            "https://dynamicontology.com/uad36/constraint/0100.0099"
        ),
        "otdd_id": "IT-33R5C1",
    }

    result = route_unresolved_constraint(
        constraint=constraint,
        stage_name="constraint-behavior-classification",
        reason="previously unknown constraint behavior",
    )

    # The unresolved constraint is explicitly isolated for review.
    assert (
        result.constraint_id
        == "https://dynamicontology.com/uad36/constraint/0100.0099"
    )
    assert result.otdd_id == "IT-33R5C1"
    assert result.stage_name == "constraint-behavior-classification"
    assert result.reason == "previously unknown constraint behavior"
    assert result.requires_review is True

    # The unresolved constraint cannot continue through automated production.
    assert result.eligible_for_automated_production is False

    # Routing the exception records the problem rather than discarding it.
    assert result.status == "exception"
