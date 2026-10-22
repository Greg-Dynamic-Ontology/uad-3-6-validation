"""IT-33R1S2: identify a constraint that cannot be evaluated reliably.

Use published workbook rows and exercise the real production rule loader.
Only the selected in-memory test row receives a missing XML path.
"""

import logging
from dataclasses import replace
from pathlib import Path

from app.services import required_data
from app.services.gse_constraint_sources import (
    read_active_compliance_workbook_rows,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIGURATION = ROOT / "config" / "configuration.ttl"


def test_it_33_r1_s2_identify_unreliable_constraint(
    monkeypatch, caplog
):
    """Report an invalid row without preventing valid rows from loading."""
    selected_ids = ["0100.0007", "0100.0009", "0100.0010"]

    workbook = read_active_compliance_workbook_rows(
        configuration_path=CONFIGURATION,
    )

    source_rows = {}
    for row_id in selected_ids:
        matches = [
            row for row in workbook.rows
            if row["Unique ID"] == row_id
        ]
        assert len(matches) == 1, (
            f"The published workbook must contain exactly one {row_id}."
        )
        source_rows[row_id] = dict(matches[0])

    rows = [dict(source_rows[row_id]) for row_id in selected_ids]
    rows[1][" xPath"] = ""
    original_rows = tuple(dict(row) for row in rows)

    selected_workbook = replace(workbook, rows=tuple(rows))

    def read_selected_workbook(*, configuration_path):
        assert Path(configuration_path).resolve() == CONFIGURATION.resolve()
        return selected_workbook

    expected = [
        {
            **row,
            "_source_document": str(workbook.workbook_path),
            "_source_sheet": workbook.worksheet_name,
        }
        for row in (rows[0], rows[2])
    ]

    required_data.load_required_rules.cache_clear()
    try:
        with monkeypatch.context() as patch:
            patch.setattr(
                required_data,
                "read_active_compliance_workbook_rows",
                read_selected_workbook,
            )
            with caplog.at_level(
                logging.ERROR,
                logger=required_data.__name__,
            ):
                loaded = required_data.load_required_rules(
                    configuration_path=CONFIGURATION,
                )

        # The invalid middle row must not stop valid rows from loading.
        assert list(loaded) == expected
        assert "0100.0009" not in {
            row["Unique ID"] for row in loaded
        }

        errors = [
            record
            for record in caplog.records
            if record.name == required_data.__name__
            and record.levelno >= logging.ERROR
        ]
        assert len(errors) == 1
        error = errors[0]
        assert getattr(error, "row_id", None) == "0100.0009"
        assert getattr(error, "configuration_field", None) == " xPath"
        assert "missing" in error.getMessage().lower()
        assert "path" in error.getMessage().lower()

        # Do not invent a replacement path or modify the supplied rows.
        assert selected_workbook.rows == original_rows
        assert selected_workbook.rows[1][" xPath"] == ""
        assert source_rows["0100.0009"][" xPath"]
    finally:
        required_data.load_required_rules.cache_clear()