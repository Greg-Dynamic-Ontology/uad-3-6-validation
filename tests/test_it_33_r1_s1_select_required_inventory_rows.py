"""IT-33R1S1 — Select inventory rows supported by the required-data evaluator."""

import csv

from app.services import required_data


def test_it_33_r1_s1_select_required_inventory_rows(tmp_path, monkeypatch):
    """
    Rule: Load the selected required-data constraints without changing
    governed identity or meaning.

    Scenario: Select inventory rows supported by the required-data evaluator.
    """
    selected_ids = {"0100.0007", "0100.0009"}

    with required_data.RULE_FILE.open(
        encoding="utf-8-sig", newline=""
    ) as stream:
        reader = csv.DictReader(stream)
        fieldnames = reader.fieldnames
        selected_rows = [
            row for row in reader if row["Unique ID"] in selected_ids
        ]

    assert {row["Unique ID"] for row in selected_rows} == selected_ids, (
        "Test setup requires the governed AddressLineText and CityName rows."
    )

    inventory = tmp_path / "selected-required-data.csv"
    with inventory.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(selected_rows)

    monkeypatch.setattr(required_data, "RULE_FILE", inventory)
    required_data.load_required_rules.cache_clear()

    try:
        loaded = required_data.load_required_rules()

        # Selection size comes from the inventory, not a fixed fixture count.
        assert len(loaded) == 2

        # Preserve identities, meaning, severity, scope, and source fields.
        assert list(loaded) == selected_rows
        assert {row["Unique ID"] for row in loaded} == selected_ids
    finally:
        required_data.load_required_rules.cache_clear()