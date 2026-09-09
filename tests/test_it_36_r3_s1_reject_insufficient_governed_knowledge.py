"""IT-36R3S1 — reject governed source input with insufficient required knowledge."""

from __future__ import annotations

from importlib import import_module

import pytest
from rdflib import Graph


def _load_normalization_agent():
    """Load the production normalization behavior."""
    try:
        module = import_module("app.services.constraint_normalization_agent")
    except ModuleNotFoundError:
        return None

    return getattr(module, "normalize_governed_constraint", None)


def test_it_36_r3_s1_rejects_governed_source_row_with_insufficient_required_knowledge() -> None:
    """
    Feature: 1 Normalize governed constraints

    Rule: Do not invent normalized constraint knowledge when governed input is insufficient

    Scenario: Reject a governed source row with insufficient required knowledge
    """
    normalize_governed_constraint = _load_normalization_agent()

    assert normalize_governed_constraint is not None, (
        "IT-36R3S1 requires "
        "app.services.constraint_normalization_agent."
        "normalize_governed_constraint"
    )

    # The governed row identifies the constraint, but does not provide the
    # requirement, violation condition, severity, context, or source locator
    # required to construct normalized governed knowledge.
    insufficient_governed_source = {
        "unique_id": "0100.0009",
        "data_point_name": "CityName",
        "source_rule_id": "UAD1002",
    }

    graph = Graph()

    with pytest.raises(ValueError, match="Insufficient governed source knowledge"):
        normalize_governed_constraint(
            governed_source=insufficient_governed_source,
            output_graph=graph,
        )

    # Rejection must be atomic: normalization must not leave behind a partial
    # constraint graph assembled from the knowledge that happened to be present.
    assert len(graph) == 0
