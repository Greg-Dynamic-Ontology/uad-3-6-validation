"""Read governed constraint knowledge from the extracted source workbook."""

from __future__ import annotations

from pathlib import Path
import re

from openpyxl import load_workbook
from openpyxl.utils.cell import range_boundaries


EXPECTED_COLUMNS = (
    "Unique ID",
    "Primary Data Element",
    "Message ID",
    "Message Text",
    "Rule Logic",
    "Severity",
    "Property Affected",
    "Report Section",
    "Report Subsection",
    "Report Label / Value",
    "Data Point Name / Value",
    " xPath",
    "Related Value(s)",
    "Date Format",
    "Number Format",
    "Min Value",
    "Max Value",
)


def _source_locator(
    *,
    workbook_path: Path,
    worksheet_name: str,
    cell_range: str,
) -> str:
    """Build an Excel-style locator for the governed source row."""
    min_col, min_row, max_col, max_row = range_boundaries(cell_range)
    from openpyxl.utils import get_column_letter

    start = f"${get_column_letter(min_col)}${min_row}"
    end = f"${get_column_letter(max_col)}${max_row}"
    return (
        f"='[{workbook_path.name}]{worksheet_name}'!"
        f"{start}:{end}"
    )


def read_governed_constraint_row(
    *,
    workbook_path: str | Path,
    worksheet_name: str,
    cell_range: str,
) -> dict:
    """
    Materialize one governed constraint row from the extracted Excel workbook.

    The function reads the workbook values; it does not infer or manufacture
    missing governed knowledge.
    """
    path = Path(workbook_path)

    if not path.is_file():
        raise FileNotFoundError(f"Governed workbook not found: {path}")

    min_col, min_row, max_col, max_row = range_boundaries(cell_range)
    if min_row != max_row:
        raise ValueError(
            "A governed constraint row must identify exactly one worksheet row"
        )

    workbook = load_workbook(
        filename=path,
        read_only=True,
        data_only=True,
    )
    try:
        if worksheet_name not in workbook.sheetnames:
            raise ValueError(
                f"Governed worksheet not found: {worksheet_name}"
            )

        worksheet = workbook[worksheet_name]

        headers = tuple(
            worksheet.cell(row=1, column=column).value
            for column in range(min_col, max_col + 1)
        )
        if headers != EXPECTED_COLUMNS:
            raise ValueError(
                "Governed workbook columns do not match the expected "
                "UAD compliance-rules structure"
            )

        values = [
            worksheet.cell(row=min_row, column=column).value
            for column in range(min_col, max_col + 1)
        ]
    finally:
        workbook.close()

    return {
        "unique_id": values[0],
        "data_point_name": values[1],
        "source_rule_id": values[2],
        "requirement_text": values[3],
        "violation_condition": values[4],
        "severity": values[5],
        "context_fields": [
            values[6],
            values[7],
            values[8],
            values[9],
            values[10],
        ],
        "source_locator": _source_locator(
            workbook_path=path,
            worksheet_name=worksheet_name,
            cell_range=cell_range,
        ),
    }


__all__ = [
    "read_governed_constraint_row",
]
