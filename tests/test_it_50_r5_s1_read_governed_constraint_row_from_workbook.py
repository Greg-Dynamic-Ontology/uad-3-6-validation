"""IT-50R5S1 — materialize a governed constraint row from an Excel workbook."""

from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook

from app.services.governed_constraint_source_reader import (
    read_governed_constraint_row,
)


HEADERS = (
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

GOVERNED_ROW = (
    "0100.0007",
    "AddressLineText",
    "UAD1001",
    "Provide the address line for the subject property physical address.",
    "If AddressLineText is not provided",
    "Fatal",
    "Subject",
    "Subject Property",
    "{No Subsection}",
    "Physical Address",
    "AddressLineText",
    "../SUBJECT/ADDRESS/ADDRESS_LINE",
    None,
    None,
    None,
    None,
    None,
)


def _write_governed_workbook(workbook_path: Path) -> None:
    """Create a workbook with one governed constraint row for this test."""
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Compliance Rules"
    worksheet.append(HEADERS)
    worksheet.append(GOVERNED_ROW)
    workbook.save(workbook_path)
    workbook.close()


def test_it_50_r5_s1_reads_governed_constraint_row_from_workbook(
    tmp_path: Path,
) -> None:
    """The selected workbook row supplies identity, meaning, and location."""
    workbook_path = tmp_path / "governed-source.xlsx"
    _write_governed_workbook(workbook_path)

    governed_source = read_governed_constraint_row(
        workbook_path=workbook_path,
        worksheet_name="Compliance Rules",
        cell_range="A2:Q2",
    )

    assert governed_source == {
        "unique_id": "0100.0007",
        "data_point_name": "AddressLineText",
        "source_rule_id": "UAD1001",
        "requirement_text": (
            "Provide the address line for the subject property physical address."
        ),
        "violation_condition": "If AddressLineText is not provided",
        "severity": "Fatal",
        "context_fields": [
            "Subject",
            "Subject Property",
            "{No Subsection}",
            "Physical Address",
            "AddressLineText",
        ],
        "source_locator": (
            "='[governed-source.xlsx]Compliance Rules'!$A$2:$Q$2"
        ),
    }