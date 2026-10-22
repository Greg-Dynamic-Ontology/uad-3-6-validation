"""IT-33R3S2: detect a required scalar without a supplied value."""

from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from app.models.enums import Investor, Severity
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
    monkeypatch, governed_rule, text, nil_value
):
    """Produce one finding when no usable scalar value is supplied."""

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

    def selected_rules(configuration_path=None):
        return (dict(governed_rule),)

    with monkeypatch.context() as patch:
        patch.setattr(
            required_data,
            "load_required_rules",
            selected_rules,
        )
        findings = required_data.evaluate_required_data(
            root, Investor.BOTH
        )

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
        assert finding.finding == governed_rule["Message Text"]
        assert ET.tostring(root) == original_xml

        # Supplying a value without a nil marker must clear the finding.
        element.attrib.pop(nil_attribute, None)
        element.text = "100 Subject Street"

        supplied_xml = ET.tostring(root)
        assert required_data.evaluate_required_data(
            root, Investor.BOTH
        ) == []
        assert ET.tostring(root) == supplied_xml