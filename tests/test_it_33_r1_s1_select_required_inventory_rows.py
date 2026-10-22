"""IT-33R1S1: select supported governed required-data rows.

Use published workbook rows as input to the real production rule loader.
Replace only its workbook-reader boundary to select the two test rows.
"""

from dataclasses import replace
from pathlib import Path

from app.services import required_data
from app.services.gse_constraint_sources import (
    read_active_compliance_workbook_rows,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIGURATION = ROOT / "config" / "configuration.ttl"


def test_it_33_r1_s1_select_required_inventory_rows(monkeypatch):
    """Load selected constraints without changing governed meaning."""
    selected_ids = {"0100.0007", "0100.0009"}

    workbook = read_active_compliance_workbook_rows(
        configuration_path=CONFIGURATION,
    )
    selected_rows = [
        dict(row)
        for row in workbook.rows
        if row["Unique ID"] in selected_ids
    ]

    assert len(selected_rows) == len(selected_ids)
    assert {row["Unique ID"] for row in selected_rows} == selected_ids, (
        "The published workbook must supply the governed "
        "AddressLineText and CityName rows."
    )
    assert {row["Message ID"] for row in selected_rows} == {
        "UAD1001",
        "UAD1002",
    }

    selected_workbook = replace(
        workbook,
        rows=tuple(dict(row) for row in selected_rows),
    )
    expected = [
        {
            **row,
            "_source_document": str(workbook.workbook_path),
            "_source_sheet": workbook.worksheet_name,
        }
        for row in selected_rows
    ]

    def read_selected_workbook(*, configuration_path):
        assert Path(configuration_path).resolve() == CONFIGURATION.resolve()
        return selected_workbook

    required_data.load_required_rules.cache_clear()
    try:
        with monkeypatch.context() as patch:
            patch.setattr(
                required_data,
                "read_active_compliance_workbook_rows",
                read_selected_workbook,
            )

            # Exercise the real loader, not a replacement for it.
            loaded = required_data.load_required_rules(
                configuration_path=CONFIGURATION,
            )

        assert len(loaded) == len(selected_rows)
        assert list(loaded) == expected
        assert {row["Unique ID"] for row in loaded} == selected_ids

        # Loading must not modify the supplied governed rows.
        assert list(selected_workbook.rows) == selected_rows
    finally:
        required_data.load_required_rules.cache_clear()