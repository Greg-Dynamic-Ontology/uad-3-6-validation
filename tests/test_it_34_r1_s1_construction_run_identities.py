"""IT-34R1S1 — represent one construction run with explicit run, activity, and result identities."""

from __future__ import annotations

from importlib import import_module


def _load_construction_run_service():
    """Load the production construction-run service after the RED test exists."""
    try:
        module = import_module("app.services.constraint_construction_run")
    except ModuleNotFoundError:
        return None

    return getattr(module, "create_constraint_construction_run", None)


def test_it_34_r1_s1_represents_run_activity_and_result_identities() -> None:
    """
    Feature: Define and persist governed constraint-construction run knowledge

    Rule: Represent a constraint-construction execution with explicit run,
    activity, and result identities

    Scenario: Represent one construction run with explicit run, activity,
    and result identities
    """
    create_constraint_construction_run = _load_construction_run_service()

    assert create_constraint_construction_run is not None, (
        "IT-34R1S1 requires "
        "app.services.constraint_construction_run."
        "create_constraint_construction_run"
    )

    result = create_constraint_construction_run(
        batch_id="https://dynamicontology.com/uad36/batch/B2",
        constraint_id="https://dynamicontology.com/uad36/constraint/0100.0009",
        construction_stage="normalization",
        agent_id="https://dynamicontology.com/uad36/agent/normalization",
        used_knowledge=[
            "https://dynamicontology.com/uad36/source/umdp/fannie-mae/constraint/0100.0009"
        ],
        stage_status="GREEN",
    )

    # The construction run has its own governed identity.
    assert result.run_id
    assert result.run_id.startswith(
        "https://dynamicontology.com/uad36/construction/run/"
    )

    # Each construction activity has its own identity.
    assert result.activity_id
    assert result.activity_id.startswith(
        f"{result.run_id}/activity/"
    )

    # Each construction result has its own identity.
    assert result.result_id
    assert result.result_id.startswith(
        f"{result.run_id}/result/"
    )

    # The activity identifies the governed constraint being processed.
    assert (
        result.constraint_id
        == "https://dynamicontology.com/uad36/constraint/0100.0009"
    )

    # The activity identifies its construction stage.
    assert result.construction_stage == "normalization"

    # The activity identifies the agent that performed it.
    assert (
        result.agent_id
        == "https://dynamicontology.com/uad36/agent/normalization"
    )

    # The activity identifies the governed knowledge it used.
    assert result.used_knowledge == [
        "https://dynamicontology.com/uad36/source/umdp/fannie-mae/constraint/0100.0009"
    ]

    # The result identifies the activity that generated it.
    assert result.generated_by_activity == result.activity_id

    # The result identifies the governed constraint it concerns.
    assert result.result_for_constraint == result.constraint_id

    # The result records its construction-stage status.
    assert result.stage_status == "GREEN"

    # Identity generation is independent of disk-write order.
    assert result.identity_strategy == "run-activity-result"
