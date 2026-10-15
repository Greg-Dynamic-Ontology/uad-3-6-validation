"""IT-50R2S1 — preserve governed meaning across implementation identifiers."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import pytest
from rdflib import Graph, Namespace, RDF, URIRef

from app.services import constraint_normalization_agent


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_CSV = PROJECT_ROOT / "data" / "data-constraints.csv"

CONSTRAINT_VOCAB = Namespace(
    "https://dynamicontology.com/uad36/constraint-vocabulary#"
)
PROV = Namespace("http://www.w3.org/ns/prov#")

REQUIRED_COLUMNS = (
    "Unique ID",
    "Data Point Name / Value",
    "Message ID",
    "Message Text",
    "Rule Logic",
    "Severity",
)

CONTEXT_COLUMNS = (
    "Property Affected",
    "Report Section",
    "Report Subsection",
    "Report Label / Value",
    "Data Point Name / Value",
)

GOVERNED_VALUE_PREDICATES = (
    CONSTRAINT_VOCAB.governedUniqueId,
    CONSTRAINT_VOCAB.dataPointName,
    CONSTRAINT_VOCAB.sourceRuleId,
    CONSTRAINT_VOCAB.requirementText,
    CONSTRAINT_VOCAB.violationCondition,
    CONSTRAINT_VOCAB.severity,
    CONSTRAINT_VOCAB.sourceLocator,
)


def _governed_source_rows() -> list[dict[str, Any]]:
    """Supply sufficient CSV rows to the test as parameters."""

    assert SOURCE_CSV.is_file(), (
        "The governed source CSV is required for IT-50R2S1: "
        f"{SOURCE_CSV}"
    )

    rows: list[dict[str, Any]] = []

    with SOURCE_CSV.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as source_file:
        reader = csv.DictReader(source_file)

        assert reader.fieldnames is not None, (
            f"The governed source CSV has no header row: {SOURCE_CSV}"
        )

        missing_columns = set(REQUIRED_COLUMNS) - set(reader.fieldnames)
        assert not missing_columns, (
            "The governed source CSV is missing required columns: "
            f"{sorted(missing_columns)}"
        )

        for record_number, csv_row in enumerate(reader, start=2):
            if any(
                not (csv_row.get(column) or "").strip()
                for column in REQUIRED_COLUMNS
            ):
                continue

            source_locator = f"data-constraints.csv#row={record_number}"
            context_fields = [
                (csv_row.get(column) or "").strip()
                for column in CONTEXT_COLUMNS
                if (csv_row.get(column) or "").strip()
            ]

            rows.append(
                {
                    "unique_id": csv_row["Unique ID"].strip(),
                    "data_point_name": (
                        csv_row["Data Point Name / Value"].strip()
                    ),
                    "source_rule_id": csv_row["Message ID"].strip(),
                    "requirement_text": csv_row["Message Text"].strip(),
                    "violation_condition": csv_row["Rule Logic"].strip(),
                    "severity": csv_row["Severity"].strip(),
                    "context_fields": context_fields,
                    "source_locator": source_locator,
                    "source_constraint_uri": (
                        "urn:uad36:governed-source:"
                        f"{source_locator}"
                    ),
                    "_caller_record_number": record_number,
                }
            )

    assert rows, (
        "The governed CSV must supply at least one row with sufficient "
        "knowledge for IT-50R2S1."
    )
    return rows


GOVERNED_SOURCE_ROWS = _governed_source_rows()


def _normalized_constraint(graph: Graph) -> URIRef:
    """Find the sole normalized constraint resource in a row's graph."""

    constraints = list(
        graph.subjects(
            RDF.type,
            CONSTRAINT_VOCAB.NormalizedConstraint,
        )
    )
    assert len(constraints) == 1
    return constraints[0]


def _governed_meaning(graph: Graph, constraint: URIRef) -> tuple:
    """Extract governed meaning without relying on the resource IRI."""

    governed_values = tuple(
        (
            str(predicate),
            tuple(
                sorted(
                    str(value)
                    for value in graph.objects(constraint, predicate)
                )
            ),
        )
        for predicate in GOVERNED_VALUE_PREDICATES
    )

    ordered_context = []
    for context_node in graph.objects(
        constraint,
        CONSTRAINT_VOCAB.hasSourceContext,
    ):
        order_values = list(
            graph.objects(
                context_node,
                CONSTRAINT_VOCAB.contextOrder,
            )
        )
        context_values = list(
            graph.objects(
                context_node,
                CONSTRAINT_VOCAB.contextValue,
            )
        )
        assert len(order_values) == 1
        assert len(context_values) == 1
        ordered_context.append(
            (
                int(order_values[0]),
                str(context_values[0]),
            )
        )

    provenance = tuple(
        sorted(
            str(source)
            for source in graph.objects(
                constraint,
                PROV.wasDerivedFrom,
            )
        )
    )

    return (
        governed_values,
        tuple(sorted(ordered_context)),
        provenance,
    )


@pytest.mark.parametrize(
    "governed_source",
    GOVERNED_SOURCE_ROWS,
    ids=[
        f"source-row-{row['_caller_record_number']}"
        for row in GOVERNED_SOURCE_ROWS
    ],
)
def test_it_50_r2_s1_preserves_governed_meaning_independent_of_implementation(
    governed_source: dict[str, Any],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Changing the implementation IRI namespace preserves row meaning."""

    first_output = (
        tmp_path
        / f"implementation-a-row-{governed_source['_caller_record_number']}.ttl"
    )
    first_result = (
        constraint_normalization_agent.normalize_governed_constraint_to_file(
            governed_source=governed_source,
            output_path=first_output,
        )
    )

    first_graph = Graph()
    first_graph.parse(first_output, format="turtle")
    first_constraint = _normalized_constraint(first_graph)

    alternate_namespace = Namespace(
        "https://example.invalid/alternate-implementation/constraint/"
    )
    monkeypatch.setattr(
        constraint_normalization_agent,
        "UADCON",
        alternate_namespace,
    )

    second_output = (
        tmp_path
        / f"implementation-b-row-{governed_source['_caller_record_number']}.ttl"
    )
    second_result = (
        constraint_normalization_agent.normalize_governed_constraint_to_file(
            governed_source=governed_source,
            output_path=second_output,
        )
    )

    second_graph = Graph()
    second_graph.parse(second_output, format="turtle")
    second_constraint = _normalized_constraint(second_graph)

    assert first_output.is_file()
    assert second_output.is_file()

    # An implementation-specific resource IRI may change.
    assert first_constraint != second_constraint

    # Governed values, context, and source provenance remain unchanged.
    assert _governed_meaning(
        first_graph,
        first_constraint,
    ) == _governed_meaning(
        second_graph,
        second_constraint,
    )

    assert first_result.unique_id == governed_source["unique_id"]
    assert second_result.unique_id == governed_source["unique_id"]
    assert first_result.data_point_name == governed_source["data_point_name"]
    assert second_result.data_point_name == governed_source["data_point_name"]
    assert first_result.source_rule_id == governed_source["source_rule_id"]
    assert second_result.source_rule_id == governed_source["source_rule_id"]

    # The normalized representation contains no SHACL-specific terms.
    shacl_namespace = "http://www.w3.org/ns/shacl#"
    for graph in (first_graph, second_graph):
        for subject, predicate, obj in graph:
            for term in (subject, predicate, obj):
                if isinstance(term, URIRef):
                    assert not str(term).startswith(shacl_namespace)