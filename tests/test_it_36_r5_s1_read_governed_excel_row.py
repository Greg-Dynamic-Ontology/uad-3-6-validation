"""IT-36R5S1 — read a governed constraint row from the governed Excel workbook."""

from __future__ import annotations

from importlib import import_module
from pathlib import Path

import pytest


# This is the governed physical location established by extracting the
# Fannie Mae specification ZIP into the project.
GOVERNED_WORKBOOK = Path(
    "specs/FannieMae/appendix-h-1-uad-compliance-rules-urar.xlsx"
)
GOVERNED_WORKSHEET = "UAD Compliance Rules(Marked up)"
GOVERNED_RANGE = "A3:Q3"


def _load_governed_source_reader():
    """Load the production workbook reader after the RED test exists."""
    try:
        module = import_module("app.services.governed_constraint_source_reader")
    except ModuleNotFoundError:
        return None

    return getattr(module, "read_governed_constraint_row", None)


def test_it_36_r5_s1_reads_governed_constraint_row_from_governed_excel_workbook() -> None:
    """
    Feature: 1 Normalize governed constraints

    Rule: Normalize constraints from the governed source workbook

    Scenario: Read a governed constraint row from the governed Excel workbook
    """
    read_governed_constraint_row = _load_governed_source_reader()

    assert read_governed_constraint_row is not None, (
        "IT-36R5S1 requires "
        "app.services.governed_constraint_source_reader."
        "read_governed_constraint_row"
    )

    if not GOVERNED_WORKBOOK.exists():
        pytest.fail(
            "IT-36R5S1 requires the actual governed workbook at "
            f"{GOVERNED_WORKBOOK}"
        )

    governed_source = read_governed_constraint_row(
        workbook_path=GOVERNED_WORKBOOK,
        worksheet_name=GOVERNED_WORKSHEET,
        cell_range=GOVERNED_RANGE,
    )

    assert governed_source["unique_id"] == "0100.0009"
    assert governed_source["data_point_name"] == "CityName"
    assert governed_source["source_rule_id"] == "UAD1002"
    assert governed_source["requirement_text"] == (
        "Provide the city name for the subject property physical address."
    )
    assert governed_source["violation_condition"] == "If CityName is not provided"
    assert governed_source["severity"] == "Fatal"

    assert governed_source["context_fields"] == [
        "Subject",
        "Subject Property",
        "{No Subsection}",
        "Physical Address",
        "CityName",
    ]

    # The source locator records the actual governed workbook artifact and
    # the exact worksheet/range from which this knowledge was materialized.
    assert governed_source["source_locator"] == (
        "='[appendix-h-1-uad-compliance-rules-urar.xlsx]"
        "UAD Compliance Rules(Marked up)'!$A$3:$Q$3"
    )
