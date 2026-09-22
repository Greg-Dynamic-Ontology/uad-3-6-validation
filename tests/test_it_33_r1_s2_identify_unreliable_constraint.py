"""IT-33R1S2 — Identify a constraint that cannot be evaluated reliably."""

import csv
import logging

from app.services import required_data


def test_it_33_r1_s2_identify_unreliable_constraint(
    tmp_path, monkeypatch, caplog
):
    """
    Scenario: Identify a constraint that cannot be evaluated reliably.

    Report configuration errors through structured logging while retaining
    the existing loader's return contract for executable rules.
    """
    selected_ids = ["0100.0007", "0100.0009", "0100.0010"]

    with required_data.RULE_FILE.open(
        encoding="utf-8-sig", newline=""
    ) as stream:
        reader = csv.DictReader(stream)
        fieldnames = reader.fieldnames
        source_rows = {
            row["Unique ID"]: row
            for row in reader
            if row["Unique ID"] in selected_ids
        }

    assert set(source_rows) == set(selected_ids), (
        "Test setup requires the three governed address rows."
    )

    rows = [dict(source_rows[row_id]) for row_id in selected_ids]
    rows[1][" xPath"] = ""

    inventory = tmp_path / "selected-required-data.csv"
    with inventory.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    original_inventory = inventory.read_bytes()
    monkeypatch.setattr(required_data, "RULE_FILE", inventory)
    required_data.load_required_rules.cache_clear()

    try:
        with caplog.at_level(
            logging.ERROR, logger=required_data.__name__
        ):
            loaded = required_data.load_required_rules()

        # The invalid middle row must not stop valid rows from loading.
        assert list(loaded) == [rows[0], rows[2]]
        assert "0100.0009" not in {
            row["Unique ID"] for row in loaded
        }

        # Identify the source row and configuration problem explicitly.
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

        # Do not invent a replacement path or rewrite the inventory.
        assert inventory.read_bytes() == original_inventory
    finally:
        required_data.load_required_rules.cache_clear()