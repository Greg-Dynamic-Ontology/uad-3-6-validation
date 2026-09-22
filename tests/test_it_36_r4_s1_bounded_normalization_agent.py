"""IT-36R4S1 — normalization agent returns only contracted output or exception."""

from __future__ import annotations

from importlib import import_module

from rdflib import Graph


def _load_agent_contract():
    """Load the bounded normalization-agent contract after the RED test exists."""
    try:
        module = import_module("app.services.constraint_normalization_agent")
    except ModuleNotFoundError:
        return None

    return getattr(module, "execute_constraint_normalization", None)


def test_it_36_r4_s1_returns_only_contracted_output_or_contracted_exception() -> None:
    """
    Feature: 1 Normalize governed constraints

    Rule: The normalization agent behaves as a bounded worker

    Scenario: Return only contracted output or a contracted exception
    """
    execute_constraint_normalization = _load_agent_contract()

    assert execute_constraint_normalization is not None, (
        "IT-36R4S1 requires "
        "app.services.constraint_normalization_agent."
        "execute_constraint_normalization"
    )

    sufficient_source = {
        "unique_id": "0100.0009",
        "data_point_name": "CityName",
        "source_rule_id": "UAD1002",
        "requirement_text": (
            "Provide the city name for the subject property physical address."
        ),
        "violation_condition": "If CityName is not provided",
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

    success_graph = Graph()
    success = execute_constraint_normalization(
        governed_source=sufficient_source,
        output_graph=success_graph,
    )

    assert success.status == "success"
    assert success.output is not None
    assert success.exception is None
    assert success.output.constraint_id.endswith("/0100.0009")

    insufficient_source = {
        "unique_id": "0100.0009",
        "data_point_name": "CityName",
        "source_rule_id": "UAD1002",
    }

    failure_graph = Graph()
    failure = execute_constraint_normalization(
        governed_source=insufficient_source,
        output_graph=failure_graph,
    )

    assert failure.status == "exception"
    assert failure.output is None
    assert failure.exception is not None
    assert failure.exception.kind == "insufficient-governed-knowledge"
    assert failure.exception.constraint_id == "0100.0009"
    assert failure.exception.stage == "normalized-constraint-representation"
    assert failure.exception.requires_review is True
    assert len(failure_graph) == 0
