"""IT-50R1S1 — produce normalized RDF from governed CSV rows."""

from __future__ import annotations

import csv
from collections import defaultdict
from importlib import import_module
from pathlib import Path
from typing import Any

import pytest
from rdflib import Graph, Literal, Namespace, RDF, URIRef


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_CSV = PROJECT_ROOT / "data" / "data-constraints.csv"
CONSTRAINT_AGENT_MODULE = "app.services.constraint_normalization_agent"

CONSTRAINT_VOCAB = Namespace(
    "https://dynamicontology.com/uad36/constraint-vocabulary#"
)
PROV = Namespace("http://www.w3.org/ns/prov#")

REQUIRED_SOURCE_COLUMNS = (
    "Unique ID",
    "Data Point Name / Value",
    "Message ID",
    "Message Text",
    "Rule Logic",
    "Severity",
)

CONTEXT_SOURCE_COLUMNS = (
    "Property Affected",
    "Report Section",
    "Report Subsection",
    "Report Label / Value",
    "Data Point Name / Value",
)


def _source_rows() -> list[dict[str, Any]]:
    """Read sufficient governed rows and prepare them as caller parameters."""

    assert SOURCE_CSV.is_file(), (
        "The governed source CSV is required for IT-50R1S1: "
        f"{SOURCE_CSV}"
    )

    prepared_rows: list[dict[str, Any]] = []

    with SOURCE_CSV.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as source_file:
        reader = csv.DictReader(source_file)

        assert reader.fieldnames is not None, (
            f"The governed source CSV has no header row: {SOURCE_CSV}"
        )

        missing_columns = set(REQUIRED_SOURCE_COLUMNS) - set(reader.fieldnames)
        assert not missing_columns, (
            "The governed source CSV is missing required columns: "
            f"{sorted(missing_columns)}"
        )

        for record_number, csv_row in enumerate(reader, start=2):
            # Sufficient-source behavior is exercised here. Missing or
            # ambiguous source knowledge belongs to its dedicated scenarios.
            if any(
                not (csv_row.get(column) or "").strip()
                for column in REQUIRED_SOURCE_COLUMNS
            ):
                continue

            source_locator = f"data-constraints.csv#row={record_number}"
            context_fields = [
                (csv_row.get(column) or "").strip()
                for column in CONTEXT_SOURCE_COLUMNS
                if (csv_row.get(column) or "").strip()
            ]

            # The caller supplies a row-level source identity. It remains
            # distinct when the governed Unique ID value is reused.
            source_constraint_uri = (
                "urn:uad36:governed-source:"
                f"{source_locator}"
            )

            prepared_rows.append(
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
                    "source_constraint_uri": source_constraint_uri,
                    "_caller_record_number": record_number,
                }
            )

    assert prepared_rows, (
        "The governed CSV must supply at least one row with sufficient "
        "knowledge for IT-50R1S1."
    )
    return prepared_rows


GOVERNED_SOURCE_ROWS = _source_rows()


def _load_file_writer():
    """Load the production behavior that writes normalized Turtle."""

    try:
        module = import_module(CONSTRAINT_AGENT_MODULE)
    except ModuleNotFoundError as error:
        if error.name != CONSTRAINT_AGENT_MODULE:
            raise
        pytest.fail(
            "IT-50R1S1 requires "
            "app.services.constraint_normalization_agent before normalized "
            "constraint RDF can be written.",
            pytrace=False,
        )

    normalize_to_file = getattr(
        module,
        "normalize_governed_constraint_to_file",
        None,
    )
    assert callable(normalize_to_file), (
        "IT-50R1S1 requires "
        "normalize_governed_constraint_to_file("
        "governed_source, output_path) to write normalized RDF."
    )
    return normalize_to_file


@pytest.mark.parametrize(
    "governed_source",
    GOVERNED_SOURCE_ROWS,
    ids=[
        f"source-row-{row['_caller_record_number']}"
        for row in GOVERNED_SOURCE_ROWS
    ],
)
def test_it_50_r1_s1_writes_traceable_normalized_constraint_rdf(
    governed_source: dict[str, Any],
    tmp_path: Path,
) -> None:
    """Write RDF for one caller-supplied governed CSV row."""

    normalize_to_file = _load_file_writer()
    record_number = governed_source["_caller_record_number"]
    output_path = tmp_path / f"source-row-{record_number}.ttl"

    result = normalize_to_file(
        governed_source=governed_source,
        output_path=output_path,
    )

    assert output_path.is_file(), (
        "The production normalizer must write RDF to the requested output "
        f"path: {output_path}"
    )

    graph = Graph()
    graph.parse(output_path, format="turtle")
    normalized_constraint = URIRef(result.constraint_id)

    assert (
        normalized_constraint,
        RDF.type,
        CONSTRAINT_VOCAB.NormalizedConstraint,
    ) in graph

    expected_literals = (
        ("governedUniqueId", governed_source["unique_id"]),
        ("dataPointName", governed_source["data_point_name"]),
        ("sourceRuleId", governed_source["source_rule_id"]),
        ("requirementText", governed_source["requirement_text"]),
        ("violationCondition", governed_source["violation_condition"]),
        ("severity", governed_source["severity"]),
        ("sourceLocator", governed_source["source_locator"]),
    )

    for predicate_name, expected_value in expected_literals:
        assert (
            normalized_constraint,
            getattr(CONSTRAINT_VOCAB, predicate_name),
            Literal(expected_value),
        ) in graph

    expected_source_uri = URIRef(
        governed_source["source_constraint_uri"]
    )
    assert (
        normalized_constraint,
        PROV.wasDerivedFrom,
        expected_source_uri,
    ) in graph

    actual_context = sorted(
        (
            int(order),
            str(value),
        )
        for context_node in graph.objects(
            normalized_constraint,
            CONSTRAINT_VOCAB.hasSourceContext,
        )
        for order in graph.objects(
            context_node,
            CONSTRAINT_VOCAB.contextOrder,
        )
        for value in graph.objects(
            context_node,
            CONSTRAINT_VOCAB.contextValue,
        )
    )
    expected_context = [
        (index, value)
        for index, value in enumerate(
            governed_source["context_fields"],
            start=1,
        )
    ]
    assert actual_context == expected_context

    shacl_namespace = "http://www.w3.org/ns/shacl#"
    assert all(
        not str(predicate).startswith(shacl_namespace)
        for _, predicate, _ in graph
    ), "Normalized constraint RDF must not depend on SHACL representation."

    assert result.unique_id == governed_source["unique_id"]
    assert result.data_point_name == governed_source["data_point_name"]
    assert result.source_rule_id == governed_source["source_rule_id"]


def test_it_50_r1_s1_keeps_reused_unique_ids_as_distinct_constraints(
    tmp_path: Path,
) -> None:
    """Do not merge separate governed rows that reuse a Unique ID."""

    rows_by_unique_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for governed_source in GOVERNED_SOURCE_ROWS:
        rows_by_unique_id[governed_source["unique_id"]].append(
            governed_source
        )

    duplicate_rows = next(
        (
            rows
            for rows in rows_by_unique_id.values()
            if len(rows) > 1
        ),
        None,
    )
    if duplicate_rows is None:
        pytest.skip(
            "The current governed CSV has no sufficient rows that reuse "
            "a Unique ID."
        )

    normalize_to_file = _load_file_writer()
    results = []

    for governed_source in duplicate_rows:
        record_number = governed_source["_caller_record_number"]
        output_path = tmp_path / f"reused-unique-id-row-{record_number}.ttl"
        results.append(
            normalize_to_file(
                governed_source=governed_source,
                output_path=output_path,
            )
        )

    constraint_ids = {
        result.constraint_id
        for result in results
    }
    assert len(constraint_ids) == len(duplicate_rows), (
        "Separate governed CSV rows that reuse a Unique ID must still "
        "produce distinct normalized constraint resources."
    )