"""IT-36R5S2 — produce normalized RDF from an actual governed workbook row."""

from __future__ import annotations

from importlib import import_module
from pathlib import Path

from rdflib import Graph, Literal, Namespace, RDF, URIRef


GOVERNED_WORKBOOK = Path(
    "specs/FannieMae/appendix-h-1-uad-compliance-rules-urar.xlsx"
)
GOVERNED_WORKSHEET = "UAD Compliance Rules(Marked up)"
GOVERNED_RANGE = "A3:Q3"

UADCON = Namespace("https://dynamicontology.com/uad36/constraint/")
UADCV = Namespace("https://dynamicontology.com/uad36/constraint-vocabulary#")


def _load_workbook_normalization_process():
    """Load the integrated workbook-to-normalized-RDF behavior after RED exists."""
    try:
        module = import_module("app.services.constraint_normalization_agent")
    except ModuleNotFoundError:
        return None

    return getattr(module, "normalize_governed_constraint_from_workbook", None)


def test_it_36_r5_s2_produces_normalized_rdf_from_actual_governed_workbook_row() -> None:
    """
    Feature: 1 Normalize governed constraints

    Rule: Normalize constraints from the governed source workbook

    Scenario: Produce normalized RDF from an actual governed workbook row
    """
    normalize_from_workbook = _load_workbook_normalization_process()

    assert normalize_from_workbook is not None, (
        "IT-36R5S2 requires "
        "app.services.constraint_normalization_agent."
        "normalize_governed_constraint_from_workbook"
    )

    assert GOVERNED_WORKBOOK.is_file(), (
        "IT-36R5S2 requires the governed workbook at "
        f"{GOVERNED_WORKBOOK}"
    )

    graph = Graph()

    result = normalize_from_workbook(
        workbook_path=GOVERNED_WORKBOOK,
        worksheet_name=GOVERNED_WORKSHEET,
        cell_range=GOVERNED_RANGE,
        output_graph=graph,
    )

    constraint_id = URIRef(f"{UADCON}0100.0009")
    expected_locator = (
        "='[appendix-h-1-uad-compliance-rules-urar.xlsx]"
        "UAD Compliance Rules(Marked up)'!$A$3:$Q$3"
    )

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
        Literal(expected_locator),
    ) in graph

    expected_context = [
        "Subject",
        "Subject Property",
        "{No Subsection}",
        "Physical Address",
        "CityName",
    ]
    for index, value in enumerate(expected_context, start=1):
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
            Literal(value),
        ) in graph
