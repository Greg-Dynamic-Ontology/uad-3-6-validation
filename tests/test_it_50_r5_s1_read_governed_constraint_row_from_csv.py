"""IT-50R5S1: read a governed constraint row directly from the CSV."""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path
from typing import Any

from app.services.governed_constraint_source_reader import (
    read_governed_constraint_row_from_csv,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
GOVERNED_CSV = PROJECT_ROOT / "data" / "data-constraints.csv"

REQUIRED_SOURCE_COLUMNS = (
    "Unique ID",
    "Primary Data Element",
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


def _source_value(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _read_unique_populated_source_row() -> tuple[int, dict[str, str]]:
    assert GOVERNED_CSV.is_file(), (
        f"The governed source CSV is missing: {GOVERNED_CSV}"
    )

    with GOVERNED_CSV.open("r", encoding="utf-8-sig", newline="") as source_file:
        reader = csv.DictReader(source_file)
        assert reader.fieldnames is not None, (
            "The governed source CSV has no header."
        )
        rows = list(reader)

    unique_id_counts = Counter(
        _source_value(row.get("Unique ID"))
        for row in rows
        if _source_value(row.get("Unique ID"))
    )

    for row_number, row in enumerate(rows, start=2):
        unique_id = _source_value(row.get("Unique ID"))
        if (
            unique_id
            and unique_id_counts[unique_id] == 1
            and all(_source_value(row.get(column)) for column in REQUIRED_SOURCE_COLUMNS)
        ):
            return row_number, {
                column: _source_value(value)
                for column, value in row.items()
                if column is not None
            }

    raise AssertionError(
        "The governed source CSV must contain a uniquely selectable row with "
        "all required normalization knowledge."
    )


def test_it_50_r5_s1_reads_governed_constraint_row_from_csv() -> None:
    """The CSV row supplies source knowledge and its governed location."""
    row_number, source_row = _read_unique_populated_source_row()
    unique_id = source_row["Unique ID"]

    governed_source = read_governed_constraint_row_from_csv(
        csv_path=GOVERNED_CSV,
        unique_id=unique_id,
    )

    locator = f"{GOVERNED_CSV.name}#row={row_number}"

    assert governed_source == {
        "unique_id": unique_id,
        "primary_data_element": source_row["Primary Data Element"],
        "source_rule_id": source_row["Message ID"],
        "requirement_text": source_row["Message Text"],
        "violation_condition": source_row["Rule Logic"],
        "severity": source_row["Severity"],
        "property_affected": source_row["Property Affected"],
        "report_section": source_row["Report Section"],
        "report_subsection": source_row["Report Subsection"],
        "report_label_or_value": source_row["Report Label / Value"],
        "data_point_name_or_value": source_row["Data Point Name / Value"],
        "xpath": source_row[" xPath"],
        "related_values": source_row["Related Value(s)"],
        "date_format": source_row["Date Format"],
        "number_format": source_row["Number Format"],
        "min_value": source_row["Min Value"],
        "max_value": source_row["Max Value"],
        "context_fields": tuple(source_row[column] for column in CONTEXT_COLUMNS),
        "source_locator": locator,
        "source_constraint_uri": f"urn:uad36:governed-source:{locator}",
    }