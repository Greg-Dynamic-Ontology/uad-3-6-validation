"""IT-36R3S2 — reject ambiguous governed source knowledge."""

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


def test_it_36_r3_s2_rejects_ambiguous_governed_source_knowledge() -> None:
    """
    Feature: 1 Normalize governed constraints

    Rule: Do not invent normalized constraint knowledge when governed input is insufficient

    Scenario: Reject ambiguous governed source knowledge
    """
    normalize_governed_constraint = _load_normalization_agent()

    assert normalize_governed_constraint is not None, (
        "IT-36R3S2 requires "
        "app.services.constraint_normalization_agent."
        "normalize_governed_constraint"
    )

    # The governed source supplies two competing values for one field whose
    # normalized representation requires one governed value. Normalization
    # must not choose between them.
    ambiguous_governed_source = {
        "unique_id": "0100.0009",
        "data_point_name": "CityName",
        "source_rule_id": "UAD1002",
        "requirement_text": (
            "Provide the city name for the subject property physical address."
        ),
        "violation_condition": [
            "If CityName is not provided",
            "If CityName is blank",
        ],
        "severity": "Fatal",
        "context_fields": [
            "Subject",
            "Subject Property",
            "{No Subsection}",
            "Physical Address",
            "CityName",
        ],
        "source_locator": (
            "='[Appendix H-1 UAD Compliance Rules - URAR.xlsm]"
            "UAD Compliance Rules(Marked up)'!$A$3:$Q$3"
        ),
    }

    graph = Graph()

    with pytest.raises(ValueError, match="Ambiguous governed source knowledge"):
        normalize_governed_constraint(
            governed_source=ambiguous_governed_source,
            output_graph=graph,
        )

    # Ambiguity must be rejected before any normalized constraint knowledge
    # is written. The agent may not statistically or procedurally choose one
    # governed meaning over another.
    assert len(graph) == 0
