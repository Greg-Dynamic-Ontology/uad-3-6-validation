"""IT-33R5S2 — Prove the positive control and each supported negative fixture."""

import csv
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from app.models.enums import Investor, Severity
from app.services import required_data


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = (
    PROJECT_ROOT
    / "data"
    / "uad36-test-suite"
    / "tests"
    / "fixtures"
    / "required_data"
)
BASELINE = FIXTURES / "baseline" / "SF1_Appraisal_v1.4.xml"

with (FIXTURES / "manifest.csv").open(
    encoding="utf-8-sig", newline=""
) as stream:
    CASES = list(csv.DictReader(stream))


@pytest.fixture(scope="module")
def supported_rules():
    required_data.load_required_rules.cache_clear()
    try:
        rules = required_data.load_required_rules()
        by_id = {row["Unique ID"]: row for row in rules}

        assert CASES, "The manifest must contain fixture cases."
        assert len(by_id) == len(rules), "Source row IDs must be unique."
        assert set(by_id) == {case["row_id"] for case in CASES}, (
            "Fixture coverage must match the supported constraint set."
        )

        yield by_id
    finally:
        required_data.load_required_rules.cache_clear()


def test_it_33_r5_s2_positive_control(supported_rules):
    """The complete source XML has no selected required-data findings."""
    original = BASELINE.read_bytes()
    root = ET.fromstring(original)
    original_tree = ET.tostring(root)

    findings = required_data.evaluate_required_data(root, Investor.BOTH)

    assert findings == []
    assert ET.tostring(root) == original_tree
    assert BASELINE.read_bytes() == original


@pytest.mark.parametrize(
    "case",
    CASES,
    ids=lambda case: f"{case['row_id']}-{case['rule_id']}",
)
def test_it_33_r5_s2_negative_fixture(case, supported_rules):
    """Each controlled defect produces exactly its expected finding."""
    rule = supported_rules[case["row_id"]]
    fixture_path = FIXTURES / "tests" / case["filename"]
    original = fixture_path.read_bytes()
    root = ET.fromstring(original)
    original_tree = ET.tostring(root)

    assert rule["Message ID"] == case["rule_id"]
    assert rule["Primary Data Element"] == case["primary_data_element"]

    lookup_path = "." + case["xml_path_context"]
    parent_path = lookup_path.rsplit("/", 1)[0]
    assert len(root.findall(parent_path, required_data.NS)) == 1
    assert root.findall(lookup_path, required_data.NS) == []

    findings = required_data.evaluate_required_data(root, Investor.BOTH)

    # Exactly one finding also rejects unexpected findings for other rows.
    assert len(findings) == 1, (
        f"Expected only the defect for {case['row_id']}; "
        f"received {[(f.row_id, f.data_location) for f in findings]}"
    )

    finding = findings[0]
    assert finding.row_id == case["row_id"]
    assert finding.rule_id == rule["Message ID"]
    assert finding.primary_data_element == rule["Primary Data Element"]
    assert finding.property_affected == rule["Property Affected"]
    assert finding.data_location == case["xml_path_context"]
    assert finding.severity == Severity(rule["Severity"].lower())
    assert finding.violation_kind == "MissingRequiredValue"
    assert finding.finding == rule["Message Text"]
    assert finding.expected_condition == (
        f"{rule['Primary Data Element']} must be provided."
    )

    assert finding.source is not None
    assert finding.source.source_document == "data/data-constraints.csv"
    assert finding.source.source_section == rule["Unique ID"]

    assert ET.tostring(root) == original_tree
    assert fixture_path.read_bytes() == original