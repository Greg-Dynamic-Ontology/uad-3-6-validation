"""IT-33R2S1 — Evaluate the subject property's physical address in its governed context."""

import csv
from xml.etree import ElementTree as ET

import pytest

from app.models.enums import Investor
from app.services import required_data


@pytest.mark.parametrize(
    "subject_address_content",
    [
        "",
        "<other:AddressLineText>Wrong namespace</other:AddressLineText>",
    ],
    ids=["missing-element", "wrong-namespace-element"],
)
def test_it_33_r2_s1_subject_address_context(
    tmp_path, monkeypatch, subject_address_content
):
    """
    Rule: Locate required data within its governed XML context.

    Scenario: Evaluate the subject property's physical address
    in its governed context.
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

    # Use a different prefix to verify namespace URI-based matching.
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

        assert required_data.evaluate_required_data(
            root, Investor.BOTH
        ) == []
    finally:
        required_data.load_required_rules.cache_clear()