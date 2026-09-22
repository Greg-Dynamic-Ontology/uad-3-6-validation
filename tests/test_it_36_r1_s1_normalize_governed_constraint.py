"""IT-36R1S1 — produce normalized RDF from a governed source constraint."""

from __future__ import annotations

from importlib import import_module

from rdflib import Graph, Literal, Namespace, RDF, URIRef


UADCON = Namespace("https://dynamicontology.com/uad36/constraint/")
UADCV = Namespace("https://dynamicontology.com/uad36/constraint-vocabulary#")


def _load_normalization_agent():
    """Load the production normalization behavior after the RED test exists."""
    try:
        module = import_module("app.services.constraint_normalization_agent")
    except ModuleNotFoundError:
        return None

    return getattr(module, "normalize_governed_constraint", None)


def test_it_36_r1_s1_produces_normalized_rdf_from_governed_source_constraint() -> None:
    """
    Feature: 1 Normalize governed constraints

    Rule: Produce normalized constraint RDF from sufficient governed source knowledge

    Scenario: Produce normalized RDF from a governed source constraint
    """
    normalize_governed_constraint = _load_normalization_agent()

    assert normalize_governed_constraint is not None, (
        "IT-36R1S1 requires "
        "app.services.constraint_normalization_agent."
        "normalize_governed_constraint"
    )

    governed_source = {
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

    graph = Graph()

    result = normalize_governed_constraint(
        governed_source=governed_source,
        output_graph=graph,
    )

    constraint_id = URIRef(f"{UADCON}0100.0009")

    assert result.constraint_id == str(constraint_id)
    assert result.unique_id == "0100.0009"
    assert result.data_point_name == "CityName"
    assert result.source_rule_id == "UAD1002"

    assert (constraint_id, RDF.type, UADCV.NormalizedConstraint) in graph
    assert (
        constraint_id,
        UADCV.governedUniqueId,
        Literal("0100.0009"),
    ) in graph
    assert (
        constraint_id,
        UADCV.dataPointName,
        Literal("CityName"),
    ) in graph
    assert (
        constraint_id,
        UADCV.sourceRuleId,
        Literal("UAD1002"),
    ) in graph
    assert (
        constraint_id,
        UADCV.requirementText,
        Literal(
            "Provide the city name for the subject property physical address."
        ),
    ) in graph
    assert (
        constraint_id,
        UADCV.violationCondition,
        Literal("If CityName is not provided"),
    ) in graph
    assert (
        constraint_id,
        UADCV.severity,
        Literal("Fatal"),
    ) in graph
    assert (
        constraint_id,
        UADCV.sourceLocator,
        Literal(governed_source["source_locator"]),
    ) in graph

    for index, context_value in enumerate(
        governed_source["context_fields"],
        start=1,
    ):
        context_node = URIRef(f"{constraint_id}/source-context/{index}")
        assert (
            constraint_id,
            UADCV.hasSourceContext,
            context_node,
        ) in graph
        assert (
            context_node,
            UADCV.contextOrder,
            Literal(index),
        ) in graph
        assert (
            context_node,
            UADCV.contextValue,
            Literal(context_value),
        ) in graph
