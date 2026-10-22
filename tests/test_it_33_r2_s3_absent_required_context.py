"""IT-33R2S3: account for an absent required context."""

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
    "missing_context",
    ["ADDRESS", "PROPERTY", "PROPERTIES"],
)
def test_it_33_r2_s3_absent_required_context(
    monkeypatch, governed_rule, missing_context
):
    """Report the expected path and nearest existing ancestor."""

    def qname(name):
        return f"{{{required_data.NAMESPACE}}}{name}"

    root = ET.Element(qname("MESSAGE"))
    analysis = ET.SubElement(root, qname("VALUATION_ANALYSIS"))
    expected_ancestor = analysis

    if missing_context != "PROPERTIES":
        properties = ET.SubElement(analysis, qname("PROPERTIES"))
        expected_ancestor = properties

        # Another property's address must not satisfy the subject rule
        # or become the ancestor reported for missing subject data.
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
        ancestor_path,
        required_data.NS,
    ) == [expected_ancestor]

    # Reporting must not fabricate the missing XML context.
    assert ET.tostring(root) == original_xml