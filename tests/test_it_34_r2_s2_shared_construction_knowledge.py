"""IT-34R2S2 — preserve graph relationships among shared construction knowledge."""

from __future__ import annotations

from importlib import import_module


def _load_shared_knowledge_linker():
    """Load the production graph-linking behavior after the RED test exists."""
    try:
        module = import_module("app.services.constraint_construction_run")
    except ModuleNotFoundError:
        return None

    return getattr(module, "link_shared_construction_knowledge", None)


def test_it_34_r2_s2_preserves_shared_construction_knowledge_as_graph() -> None:
    """
    Feature: Define and persist governed constraint-construction run knowledge

    Rule: Construction-run knowledge must preserve temporal and causal
    relationships during concurrent execution

    Scenario: Preserve graph relationships among shared construction knowledge
    """
    link_shared_construction_knowledge = _load_shared_knowledge_linker()

    assert link_shared_construction_knowledge is not None, (
        "IT-34R2S2 requires "
        "app.services.constraint_construction_run."
        "link_shared_construction_knowledge"
    )

    shared_result_id = (
        "https://dynamicontology.com/uad36/construction/run/run-1/"
        "result/context-result-42"
    )
    activity_a_id = (
        "https://dynamicontology.com/uad36/construction/run/run-1/"
        "activity/behavior-42"
    )
    activity_b_id = (
        "https://dynamicontology.com/uad36/construction/run/run-1/"
        "activity/shacl-preparation-42"
    )

    relationship = link_shared_construction_knowledge(
        knowledge_id=shared_result_id,
        consuming_activity_ids=[activity_a_id, activity_b_id],
    )

    # Both activities consume the same governed result identity.
    assert relationship.knowledge_id == shared_result_id
    assert relationship.consuming_activity_ids == [
        activity_a_id,
        activity_b_id,
    ]

    # Shared knowledge is represented once, not copied to manufacture
    # separate parent-child branches.
    assert relationship.knowledge_instance_count == 1

    # Neither consumer is designated as the parent of the shared knowledge
    # or of the other consumer.
    assert relationship.parent_activity_id is None

    # The representation explicitly preserves graph semantics.
    assert relationship.topology == "directed-graph"
