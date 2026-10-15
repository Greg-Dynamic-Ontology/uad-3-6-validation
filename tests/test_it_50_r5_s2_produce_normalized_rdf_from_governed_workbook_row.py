"""IT-50R5S2 — normalize a row read from the governed workbook."""

from __future__ import annotations

from pathlib import Path

from rdflib import Graph, Literal, Namespace, RDF, URIRef

from app.services.constraint_normalization_agent import (
    normalize_governed_constraint_from_workbook,
)


CONSTRAINT = Namespace("https://dynamicontology.com/uad36/constraint/")
CONSTRAINT_VOCAB = Namespace(
    "https://dynamicontology.com/uad36/constraint-vocabulary#"
)

EXPECTED_CONSTRAINT = URIRef(
    "https://dynamicontology.com/uad36/constraint/0100.0007"
)
EXPECTED_SOURCE_LOCATOR = (
    "='[data-constraints.xlsx]Sheet1'!$A$2:$Q$2"
)


def test_it_50_r5_s2_produces_normalized_rdf_from_governed_workbook_row() -> None:
    """The actual governed workbook row produces traceable normalized RDF."""
    project_root = Path(__file__).resolve().parents[1]
    workbook_path = project_root / "data" / "data-constraints.xlsx"

    assert workbook_path.is_file(), (
        "The governed source workbook is required for IT-50R5S2: "
        f"{workbook_path}"
    )

    output_graph = Graph()
    result = normalize_governed_constraint_from_workbook(
        workbook_path=workbook_path,
        worksheet_name="Sheet1",
        cell_range="A2:Q2",
        output_graph=output_graph,
    )

    assert (
        EXPECTED_CONSTRAINT,
        RDF.type,
        CONSTRAINT_VOCAB.NormalizedConstraint,
    ) in output_graph
    assert (
        EXPECTED_CONSTRAINT,
        CONSTRAINT_VOCAB.governedUniqueId,
        Literal("0100.0007"),
    ) in output_graph
    assert (
        EXPECTED_CONSTRAINT,
        CONSTRAINT_VOCAB.dataPointName,
        Literal("AddressLineText"),
    ) in output_graph
    assert (
        EXPECTED_CONSTRAINT,
        CONSTRAINT_VOCAB.sourceRuleId,
        Literal("UAD1001"),
    ) in output_graph
    assert (
        EXPECTED_CONSTRAINT,
        CONSTRAINT_VOCAB.requirementText,
        Literal(
            "Provide the address line for the subject property physical address."
        ),
    ) in output_graph
    assert (
        EXPECTED_CONSTRAINT,
        CONSTRAINT_VOCAB.violationCondition,
        Literal("If AddressLineText is not provided"),
    ) in output_graph
    assert (
        EXPECTED_CONSTRAINT,
        CONSTRAINT_VOCAB.severity,
        Literal("Fatal"),
    ) in output_graph
    assert (
        EXPECTED_CONSTRAINT,
        CONSTRAINT_VOCAB.sourceLocator,
        Literal(EXPECTED_SOURCE_LOCATOR),
    ) in output_graph

    context_values = {
        str(value)
        for context_node in output_graph.objects(
            EXPECTED_CONSTRAINT,
            CONSTRAINT_VOCAB.hasSourceContext,
        )
        for value in output_graph.objects(
            context_node,
            CONSTRAINT_VOCAB.contextValue,
        )
    }
    assert context_values == {
        "Subject",
        "Subject Property",
        "{No Subsection}",
        "Physical Address",
        "AddressLineText",
    }

    assert result.unique_id == "0100.0007"
    assert result.data_point_name == "AddressLineText"
    assert result.source_rule_id == "UAD1001"

    shacl_namespace = "http://www.w3.org/ns/shacl#"
    assert all(
        not str(predicate).startswith(shacl_namespace)
        for _, predicate, _ in output_graph
    )