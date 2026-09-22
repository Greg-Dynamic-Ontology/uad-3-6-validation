"""IT-33R2S2 — Check each applicable occurrence independently."""

import csv
from xml.etree import ElementTree as ET

import pytest

from app.models.enums import Investor
from app.services import required_data


@pytest.mark.parametrize("missing_index", [0, 1])
def test_it_33_r2_s2_check_each_occurrence(
    tmp_path, monkeypatch, missing_index
):
    """
    Scenario: Check each applicable occurrence independently.

    Each case has one populated subject-property address and one
    deficient address. The finding must locate only the deficient one.
    """
    with required_data.RULE_FILE.open(
        encoding="utf-8-sig", newline=""
    ) as stream:
        reader = csv.DictReader(stream)
        fieldnames = reader.fieldnames
        rows = [
            row for row in reader
            if row["Unique ID"] == "0100.0007"
        ]

    assert len(rows) == 1, "Test setup requires governed row 0100.0007."
    assert rows[0]["Message ID"] == "UAD1001"

    inventory = tmp_path / "selected-required-data.csv"
    with inventory.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    monkeypatch.setattr(required_data, "RULE_FILE", inventory)
    required_data.load_required_rules.cache_clear()

    def qname(name):
        return f"{{{required_data.NAMESPACE}}}{name}"

    root = ET.Element(qname("MESSAGE"))
    analysis = ET.SubElement(root, qname("VALUATION_ANALYSIS"))
    properties = ET.SubElement(analysis, qname("PROPERTIES"))
    addresses = []

    for index in range(2):
        property_node = ET.SubElement(
            properties,
            qname("PROPERTY"),
            {"ValuationUseType": "SubjectProperty"},
        )
        address = ET.SubElement(property_node, qname("ADDRESS"))
        addresses.append(address)

        if index != missing_index:
            ET.SubElement(address, qname("AddressLineText")).text = (
                "100 Populated Street"
            )

    try:
        findings = required_data.evaluate_required_data(root, Investor.BOTH)

        assert len(findings) == 1
        finding = findings[0]
        assert finding.row_id == "0100.0007"
        assert finding.rule_id == "UAD1001"

        # The element is missing, so resolve its existing parent address.
        location = finding.data_location
        assert location
        assert location.endswith("/m:AddressLineText")
        parent_path = location.rsplit("/", 1)[0]

        # Convert the existing // notation for ElementTree lookup.
        if parent_path.startswith("//"):
            parent_path = "." + parent_path

        located_addresses = root.findall(parent_path, required_data.NS)

        assert located_addresses == [addresses[missing_index]], (
            "The finding must identify only the deficient address; "
            f"its path resolved to {len(located_addresses)} occurrences."
        )

        # Correcting that occurrence must remove the finding.
        ET.SubElement(
            addresses[missing_index], qname("AddressLineText")
        ).text = "200 Corrected Street"

        assert required_data.evaluate_required_data(
            root, Investor.BOTH
        ) == []
    finally:
        required_data.load_required_rules.cache_clear()