"""IT-33R3S1 — Detect an absent required element."""

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

        assert CASES, "The fixture manifest must not be empty."
        assert len(by_id) == len(rules), "Source row IDs must be unique."
        assert set(by_id) == {case["row_id"] for case in CASES}, (
            "Every supported row must have fixture coverage, and every "
            "fixture must correspond to a supported row."
        )

        yield by_id
    finally:
        required_data.load_required_rules.cache_clear()


@pytest.mark.parametrize(
    "case",
    CASES,
    ids=lambda case: f"{case['row_id']}-{case['rule_id']}",
)
def test_it_33_r3_s1_detect_absent_required_element(
    case, supported_rules
):
    """
    Rule: Apply the same required-data behavior to every supported
    inventory row.

    Scenario: Detect an absent required element.
    """
    rule = supported_rules[case["row_id"]]
    assert rule["Message ID"] == case["rule_id"]
    assert rule["Primary Data Element"] == case["primary_data_element"]

    root = ET.parse(FIXTURES / "tests" / case["filename"]).getroot()
    expected_path = case["xml_path_context"]
    lookup_path = "." + expected_path
    parent_path = lookup_path.rsplit("/", 1)[0]

    # Confirm the fixture represents an absent element in an existing
    # context, rather than an absent context or a blank value.
    assert len(root.findall(parent_path, required_data.NS)) == 1
    assert root.findall(lookup_path, required_data.NS) == []

    original_xml = ET.tostring(root)
    findings = required_data.evaluate_required_data(root, Investor.BOTH)

    assert len(findings) == 1, (
        f"Expected exactly one finding for {case['row_id']}; "
        f"received {[(f.row_id, f.data_location) for f in findings]}"
    )

    finding = findings[0]
    assert finding.row_id == case["row_id"]
    assert finding.rule_id == case["rule_id"]
    assert finding.data_location == expected_path
    assert finding.severity == Severity.FATAL
    assert finding.finding == rule["Message Text"]
    assert ET.tostring(root) == original_xml