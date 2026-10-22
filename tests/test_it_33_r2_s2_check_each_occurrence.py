"""IT-33R2S2: check each applicable occurrence independently."""

from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from app.models.enums import Investor
from app.services import required_data
from app.services.gse_constraint_sources import (
    read_active_compliance_workbook_rows,
)


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def governed_rule():
    workbook = read_active_compliance_workbook_rows(
        configuration_path=ROOT / "config" / "configuration.ttl",
    )
    rows = [
        row for row in workbook.rows
        if row["Unique ID"] == "0100.0007"
        and row["Message ID"] == "UAD1001"
    ]
    assert len(rows) == 1, (
        "The published workbook must contain governed row "
        "0100.0007 / UAD1001 exactly once."
    )
    return {
        **rows[0],
        "_source_document": str(workbook.workbook_path),
        "_source_sheet": workbook.worksheet_name,
    }


@pytest.mark.parametrize("missing_index", [0, 1])
def test_it_33_r2_s2_check_each_occurrence(
    monkeypatch, governed_rule, missing_index
):
    """Locate the deficient address without using another occurrence."""

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

    def selected_rules(configuration_path=None):
        return (dict(governed_rule),)

    with monkeypatch.context() as patch:
        patch.setattr(
            required_data,
            "load_required_rules",
            selected_rules,
        )

        before = ET.tostring(root)
        findings = required_data.evaluate_required_data(
            root, Investor.BOTH
        )
        assert ET.tostring(root) == before

        assert len(findings) == 1
        finding = findings[0]
        assert finding.row_id == "0100.0007"
        assert finding.rule_id == "UAD1001"

        # Resolve the existing parent of the missing element.
        location = finding.data_location
        assert location
        assert location.endswith("/m:AddressLineText")
        parent_path = location.rsplit("/", 1)[0]

        if parent_path.startswith("//"):
            parent_path = "." + parent_path

        located_addresses = root.findall(
            parent_path,
            required_data.NS,
        )
        assert located_addresses == [addresses[missing_index]], (
            "The finding must identify only the deficient address; "
            f"its path resolved to {len(located_addresses)} occurrences."
        )

        # Correcting that occurrence must remove the finding.
        ET.SubElement(
            addresses[missing_index],
            qname("AddressLineText"),
        ).text = "200 Corrected Street"

        supplied = ET.tostring(root)
        assert required_data.evaluate_required_data(
            root, Investor.BOTH
        ) == []
        assert ET.tostring(root) == supplied