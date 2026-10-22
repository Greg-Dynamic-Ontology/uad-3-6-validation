"""IT-34R1S1: enforce a requirement when its condition is true."""

from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from app.models.enums import Investor, Severity
from app.services import required_data
from app.services.gse_constraint_sources import (
    read_active_compliance_workbook_rows,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BASELINE = (
    PROJECT_ROOT
    / "data"
    / "uad36-test-suite"
    / "tests"
    / "fixtures"
    / "required_data"
    / "baseline"
    / "SF1_Appraisal_v1.4.xml"
)
CONTEXT = (
    ".//m:VALUATION_ANALYSIS/m:PROPERTIES/"
    "m:PROPERTY[@ValuationUseType='SubjectProperty']/"
    "m:PROPERTY_DETAIL"
)
EXPECTED_PATH = (
    CONTEXT[1:] + "/m:PropertyEstateTypeOtherDescription"
)
XSI_NIL = "{http://www.w3.org/2001/XMLSchema-instance}nil"


@pytest.fixture(scope="module")
def governed_rule():
    workbook = read_active_compliance_workbook_rows(
        configuration_path=PROJECT_ROOT / "config" / "configuration.ttl",
    )
    rows = [
        row for row in workbook.rows
        if row["Unique ID"] == "0100.0053"
        and row["Message ID"] == "UAD1022"
    ]
    assert len(rows) == 1, (
        "The published workbook must contain governed row "
        "0100.0053 / UAD1022 exactly once."
    )
    rule = {
        **rows[0],
        "_source_document": str(workbook.workbook_path),
        "_source_sheet": workbook.worksheet_name,
    }
    assert rule["Rule Logic"] == (
        'If PropertyEstateType = "Other" and '
        "PropertyEstateTypeOtherDescription is not provided"
    )
    return rule


@pytest.mark.parametrize(
    "value_state",
    ["missing", "empty", "whitespace", "nil"],
)
def test_it_34_r1_s1_enforce_true_condition(
    monkeypatch, governed_rule, value_state
):
    """Require the dependent value when its governed condition is true."""
    rule = governed_rule
    original_rule = dict(rule)

    baseline_bytes = BASELINE.read_bytes()
    root = ET.fromstring(baseline_bytes)
    contexts = root.findall(CONTEXT, required_data.NS)
    assert len(contexts) == 1
    detail = contexts[0]

    trigger = detail.find("m:PropertyEstateType", required_data.NS)
    assert trigger is not None
    trigger.text = "Other"

    target_tag = (
        f"{{{required_data.NAMESPACE}}}"
        "PropertyEstateTypeOtherDescription"
    )
    for existing in list(detail.findall(target_tag)):
        detail.remove(existing)

    if value_state != "missing":
        target = ET.SubElement(detail, target_tag)
        if value_state == "whitespace":
            target.text = " \t\n "
        elif value_state == "nil":
            target.set(XSI_NIL, "true")

    original_xml = ET.tostring(root)

    def selected_rules(configuration_path=None):
        return (dict(rule),)

    with monkeypatch.context() as patch:
        patch.setattr(
            required_data,
            "load_required_rules",
            selected_rules,
        )
        findings = required_data.evaluate_required_data(
            root, Investor.BOTH
        )

        assert len(findings) == 1, (
            "A true condition with missing, blank, or nil dependent data "
            "must produce exactly one required-data finding."
        )
        finding = findings[0]
        assert finding.row_id == "0100.0053"
        assert finding.rule_id == "UAD1022"
        assert finding.severity == Severity.FATAL
        assert finding.data_location == EXPECTED_PATH
        assert finding.primary_data_element == rule["Primary Data Element"]
        assert finding.property_affected == "Subject"
        assert finding.violation_kind == "MissingRequiredValue"
        assert finding.finding == rule["Message Text"]

        assert finding.expected_condition
        assert "PropertyEstateType" in finding.expected_condition
        assert "Other" in finding.expected_condition
        assert rule["Primary Data Element"] in finding.expected_condition

        assert finding.source is not None
        assert finding.source.source_section == rule["Unique ID"]
        assert ET.tostring(root) == original_xml

        # Keep the condition true and supply the dependent value.
        for existing in list(detail.findall(target_tag)):
            detail.remove(existing)
        ET.SubElement(detail, target_tag).text = (
            "Description of the other ownership interest"
        )

        supplied_xml = ET.tostring(root)
        assert required_data.evaluate_required_data(
            root, Investor.BOTH
        ) == []
        assert ET.tostring(root) == supplied_xml

    assert rule == original_rule
    assert BASELINE.read_bytes() == baseline_bytes