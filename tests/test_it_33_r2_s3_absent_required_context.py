"""IT-33R2S3 — Account for an absent required context."""

import csv
from xml.etree import ElementTree as ET

import pytest

from app.models.enums import Investor
from app.services import required_data


@pytest.mark.parametrize(
    "missing_context",
    ["ADDRESS", "PROPERTY", "PROPERTIES"],
)
def test_it_33_r2_s3_absent_required_context(
    tmp_path, monkeypatch, missing_context
):
    """Report the expected path and nearest existing ancestor."""
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
    expected_ancestor = analysis

    if missing_context != "PROPERTIES":
        properties = ET.SubElement(analysis, qname("PROPERTIES"))
        expected_ancestor = properties

        # Another property's complete address must not satisfy the rule
        # or become the reported ancestor of the missing subject data.
        comparable = ET.SubElement(
            properties,
            qname("PROPERTY"),
            {"ValuationUseType": "ComparableProperty"},
        )
        address = ET.SubElement(comparable, qname("ADDRESS"))
        ET.SubElement(address, qname("AddressLineText")).text = (
            "100 Comparable Street"
        )

        if missing_context == "ADDRESS":
            expected_ancestor = ET.SubElement(
                properties,
                qname("PROPERTY"),
                {"ValuationUseType": "SubjectProperty"},
            )

    original_xml = ET.tostring(root)

    try:
        findings = required_data.evaluate_required_data(root, Investor.BOTH)

        assert len(findings) == 1
        finding = findings[0]
        assert finding.row_id == "0100.0007"
        assert finding.rule_id == "UAD1001"
        assert finding.data_location == (
            "//m:VALUATION_ANALYSIS/m:PROPERTIES/"
            "m:PROPERTY[@ValuationUseType='SubjectProperty']/"
            "m:ADDRESS/m:AddressLineText"
        )

        ancestor_path = finding.model_dump().get(
            "nearest_existing_ancestor"
        )
        assert ancestor_path, (
            "An absent-context finding must identify the nearest "
            "existing ancestor as well as the expected data path."
        )

        if ancestor_path.startswith("//"):
            ancestor_path = "." + ancestor_path

        assert root.findall(
            ancestor_path, required_data.NS
        ) == [expected_ancestor]

        # Reporting must not fabricate the missing XML context.
        assert ET.tostring(root) == original_xml
    finally:
        required_data.load_required_rules.cache_clear()