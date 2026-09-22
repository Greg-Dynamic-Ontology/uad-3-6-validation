"""IT-33R4S2 — Repeat evaluation with unchanged inputs."""

import csv
from copy import deepcopy
from xml.etree import ElementTree as ET

from app.models.enums import Investor
from app.services import required_data


def governed_content(finding):
    """Exclude run metadata, preserving all governed finding content."""
    return finding.model_dump(
        mode="json",
        exclude={
            "finding_id": True,
            "source": {"ingestion_timestamp"},
        },
    )


def test_it_33_r4_s2_repeat_evaluation(tmp_path, monkeypatch):
    """Return identical governed findings in a stable, duplicate-free order."""
    selected_ids = ["0100.0009", "0100.0007"]

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

    assert set(source_rows) == set(selected_ids)

    # Deliberately reverse row-ID order to test output ordering.
    inventory = tmp_path / "selected-required-data.csv"
    with inventory.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(source_rows[row_id] for row_id in selected_ids)

    monkeypatch.setattr(required_data, "RULE_FILE", inventory)
    required_data.load_required_rules.cache_clear()

    def qname(name):
        return f"{{{required_data.NAMESPACE}}}{name}"

    root = ET.Element(qname("MESSAGE"))
    analysis = ET.SubElement(root, qname("VALUATION_ANALYSIS"))
    properties = ET.SubElement(analysis, qname("PROPERTIES"))

    # Both required elements are absent in two distinct occurrences.
    for _ in range(2):
        subject = ET.SubElement(
            properties,
            qname("PROPERTY"),
            {"ValuationUseType": "SubjectProperty"},
        )
        ET.SubElement(subject, qname("ADDRESS"))

    original_xml = ET.tostring(root)
    original_inventory = inventory.read_bytes()

    try:
        original_rules = deepcopy(required_data.load_required_rules())
        runs = []

        # Verify both cached and freshly loaded configurations.
        for reload_inventory in (False, False, True):
            if reload_inventory:
                required_data.load_required_rules.cache_clear()

            findings = required_data.evaluate_required_data(
                root, Investor.BOTH
            )
            runs.append([governed_content(f) for f in findings])

            assert len(findings) == 4

            keys = [
                (finding.row_id, finding.data_location)
                for finding in findings
            ]
            assert len(set(keys)) == 4, "Duplicate findings were emitted."

            assert ET.tostring(root) == original_xml
            assert inventory.read_bytes() == original_inventory
            assert required_data.load_required_rules() == original_rules

        assert runs[0] == runs[1] == runs[2], (
            "Unchanged inputs must produce identical governed content "
            "and finding order, including after reloading the inventory."
        )

        prefix = "//m:VALUATION_ANALYSIS/m:PROPERTIES/"
        expected_keys = [
            (
                row_id,
                prefix
                + f"m:PROPERTY[{position}]"
                + "[@ValuationUseType='SubjectProperty']"
                + f"/m:ADDRESS/m:{element}",
            )
            for row_id, element in [
                ("0100.0007", "AddressLineText"),
                ("0100.0009", "CityName"),
            ]
            for position in (1, 2)
        ]

        actual_keys = [
            (finding["row_id"], finding["data_location"])
            for finding in runs[0]
        ]
        assert actual_keys == expected_keys, (
            "Findings must be ordered by source row ID and affected "
            "context occurrence, rather than inventory input order."
        )
    finally:
        required_data.load_required_rules.cache_clear()