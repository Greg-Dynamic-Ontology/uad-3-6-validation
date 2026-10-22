"""IT-33R3S3: accept a supplied required value."""

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
    monkeypatch, governed_rule, value, nil_value
):
    """Presence includes zero and false; domain checks are separate."""

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

        assert findings == [], (
            f"Supplied value {value!r} must satisfy required-data presence."
        )
        assert ET.tostring(root) == original_xml

        # Prove the rule was active rather than silently skipped.
        address.remove(element)
        missing_xml = ET.tostring(root)
        missing_findings = required_data.evaluate_required_data(
            root, Investor.BOTH
        )

        assert len(missing_findings) == 1
        assert missing_findings[0].row_id == "0100.0007"
        assert missing_findings[0].rule_id == "UAD1001"
        assert ET.tostring(root) == missing_xml