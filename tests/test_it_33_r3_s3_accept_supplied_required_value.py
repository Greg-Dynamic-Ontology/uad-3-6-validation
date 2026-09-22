"""IT-33R3S3 — Accept a supplied required value."""

import csv
from xml.etree import ElementTree as ET

import pytest

from app.models.enums import Investor
from app.services import required_data


@pytest.mark.parametrize(
    "value,nil_value",
    [
        ("100 Subject Street", None),
        (" 100 Subject Street ", None),
        ("0", None),
        ("false", None),
        ("100 Subject Street", "false"),
        ("100 Subject Street", "0"),
        ("NOT-A-VALID-DOMAIN-VALUE", None),
    ],
    ids=[
        "nonblank",
        "surrounding-whitespace",
        "zero",
        "false",
        "nil-false",
        "nil-zero",
        "presence-does-not-check-domain",
    ],
)
def test_it_33_r3_s3_accept_supplied_required_value(
    tmp_path, monkeypatch, value, nil_value
):
    """
    Scenario: Accept a supplied required value.

    Required-data validation checks presence, including zero and false.
    Domain and format validity belong to separate evaluators.
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
    subject = ET.SubElement(
        properties,
        qname("PROPERTY"),
        {"ValuationUseType": "SubjectProperty"},
    )
    address = ET.SubElement(subject, qname("ADDRESS"))
    element = ET.SubElement(address, qname("AddressLineText"))
    element.text = value

    if nil_value is not None:
        element.set(
            "{http://www.w3.org/2001/XMLSchema-instance}nil",
            nil_value,
        )

    original_xml = ET.tostring(root)

    try:
        findings = required_data.evaluate_required_data(root, Investor.BOTH)

        assert findings == [], (
            f"Supplied value {value!r} must satisfy required-data presence."
        )
        assert ET.tostring(root) == original_xml

        # Prove the rule was active rather than silently skipped.
        address.remove(element)
        missing_findings = required_data.evaluate_required_data(
            root, Investor.BOTH
        )

        assert len(missing_findings) == 1
        assert missing_findings[0].row_id == "0100.0007"
        assert missing_findings[0].rule_id == "UAD1001"
    finally:
        required_data.load_required_rules.cache_clear()