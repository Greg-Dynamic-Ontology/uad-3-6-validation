"""IT-50R5S5: reject CSV rows with blank required governed knowledge."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from app.services.governed_constraint_source_reader import (
    read_governed_constraint_row_from_csv,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
GOVERNED_CSV = PROJECT_ROOT / "data" / "data-constraints.csv"

REQUIRED_GOVERNED_KNOWLEDGE_COLUMNS = (
    "Primary Data Element",
    "Message ID",
    "Message Text",
    "Rule Logic",
    "Severity",
)


def read_governed_csv() -> tuple[list[str], list[list[str]]]:
    assert GOVERNED_CSV.is_file(), (
        "The governed source CSV is missing: "
        f"{GOVERNED_CSV}"
    )

    with GOVERNED_CSV.open("r", encoding="utf-8-sig", newline="") as source_file:
        reader = csv.reader(source_file)
        headers = next(reader, None)
        assert headers is not None, "The governed source CSV is empty."
        rows = list(reader)

    assert rows, "The governed source CSV has no data rows."
    return headers, rows


def test_it_50_r5_s5_rejects_csv_row_with_blank_required_governed_knowledge(
    tmp_path: Path,
) -> None:
    headers, rows = read_governed_csv()
    unique_id_column = headers.index("Unique ID")
    required_column_indexes = {
        column: headers.index(column)
        for column in REQUIRED_GOVERNED_KNOWLEDGE_COLUMNS
    }

    eligible_rows = [
        row
        for row in rows
        if row[unique_id_column].strip()
        and all(row[index].strip() for index in required_column_indexes.values())
    ]
    assert eligible_rows, (
        "The governed CSV must contain a row populated in its Unique ID and "
        "required knowledge columns so each blank-value case can be tested."
    )

    source_row = eligible_rows[0]
    selected_unique_id = source_row[unique_id_column]

    for column, column_index in required_column_indexes.items():
        malformed_row = list(source_row)
        malformed_row[column_index] = ""
        malformed_csv = tmp_path / f"blank-{column_index}.csv"

        with malformed_csv.open("w", encoding="utf-8", newline="") as output_file:
            writer = csv.writer(output_file)
            writer.writerow(headers)
            writer.writerow(malformed_row)

        with pytest.raises(ValueError) as raised:
            read_governed_constraint_row_from_csv(
                csv_path=malformed_csv,
                unique_id=selected_unique_id,
            )

        message = str(raised.value).lower()
        assert any(
            term in message
            for term in ("required", "blank", "empty", "missing")
        ), (
            f"Blank required governed field {column!r} should be identified "
            f"as incomplete source knowledge; got: {raised.value}"
        )