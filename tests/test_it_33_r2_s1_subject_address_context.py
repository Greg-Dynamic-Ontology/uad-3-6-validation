"""IT-33R2S1: evaluate the subject address in its governed context."""

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
    "subject_address_content",
    [
        "",
        "<other:AddressLineText>Wrong namespace</other:AddressLineText>",
    ],
    ids=["missing-element", "wrong-namespace-element"],
)
def test_it_33_r2_s1_subject_address_context(
    monkeypatch, governed_rule, subject_address_content
):
    """Find required address data only in the subject's governed context."""
    root = ET.fromstring(
        f"""
        <u:VALUATION_ANALYSIS
            xmlns:u="{required_data.NAMESPACE}"
            xmlns:other="urn:test:other">
          <u:PROPERTIES>
            <u:PROPERTY ValuationUseType="SubjectProperty">
              <u:ADDRESS>{subject_address_content}</u:ADDRESS>
            </u:PROPERTY>
            <u:PROPERTY ValuationUseType="ComparableProperty">
              <u:ADDRESS>
                <u:AddressLineText>100 Comparable Street</u:AddressLineText>
              </u:ADDRESS>
            </u:PROPERTY>
          </u:PROPERTIES>
        </u:VALUATION_ANALYSIS>
        """
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
        assert finding.data_location == (
            "//m:VALUATION_ANALYSIS/m:PROPERTIES/"
            "m:PROPERTY[@ValuationUseType='SubjectProperty']/"
            "m:ADDRESS/m:AddressLineText"
        )

        # Supplying the actual subject address must clear the finding.
        subject_address = root.find(
            "m:PROPERTIES/"
            "m:PROPERTY[@ValuationUseType='SubjectProperty']/m:ADDRESS",
            required_data.NS,
        )
        assert subject_address is not None
        ET.SubElement(
            subject_address,
            f"{{{required_data.NAMESPACE}}}AddressLineText",
        ).text = "200 Subject Street"

        supplied = ET.tostring(root)
        assert required_data.evaluate_required_data(
            root, Investor.BOTH
        ) == []
        assert ET.tostring(root) == supplied