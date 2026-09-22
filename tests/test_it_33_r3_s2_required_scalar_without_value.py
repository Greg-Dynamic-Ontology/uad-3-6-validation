"""IT-33R3S2 — Detect a required scalar element without a supplied value."""

import csv
from xml.etree import ElementTree as ET

import pytest

from app.models.enums import Investor, Severity
from app.services import required_data


@pytest.mark.parametrize(
    "text,nil_value",
    [
        (None, None),
        (" \t\n ", None),
        (None, "true"),
        (None, "1"),
        ("100 Subject Street", "true"),
    ],
    ids=[
        "empty",
        "whitespace-only",
        "nil-true",
        "nil-one",
        "nil-with-text",
    ],
)
def test_it_33_r3_s2_required_scalar_without_value(
    tmp_path, monkeypatch, text, nil_value
):
    """Produce exactly one finding when no usable scalar value is supplied."""
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
    element.text = text

    nil_attribute = "{http://www.w3.org/2001/XMLSchema-instance}nil"
    if nil_value is not None:
        element.set(nil_attribute, nil_value)

    original_xml = ET.tostring(root)

    try:
        findings = required_data.evaluate_required_data(root, Investor.BOTH)

        assert len(findings) == 1
        finding = findings[0]
        assert finding.row_id == "0100.0007"
        assert finding.rule_id == "UAD1001"
        assert finding.severity == Severity.FATAL
        assert finding.data_location == (
            "//m:VALUATION_ANALYSIS/m:PROPERTIES/"
            "m:PROPERTY[@ValuationUseType='SubjectProperty']/"
            "m:ADDRESS/m:AddressLineText"
        )
        assert finding.finding == rows[0]["Message Text"]
        assert ET.tostring(root) == original_xml

        # A supplied value without a nil marker must clear the finding.
        element.attrib.pop(nil_attribute, None)
        element.text = "100 Subject Street"

        assert required_data.evaluate_required_data(
            root, Investor.BOTH
        ) == []
    finally:
        required_data.load_required_rules.cache_clear()