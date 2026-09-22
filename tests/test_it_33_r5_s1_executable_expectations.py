"""IT-33R5S1 — Establish executable required-data expectations."""

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


def assert_expected_finding(findings, case):
    """Express the observable expectation independently of the evaluator."""
    matching = [
        finding
        for finding in findings
        if finding.row_id == case["row_id"]
    ]

    assert len(matching) == 1, (
        f"Expected one required-data finding for {case['row_id']}; "
        f"received {len(matching)}."
    )

    finding = matching[0]
    assert finding.rule_id == case["rule_id"]
    assert finding.primary_data_element == case["primary_data_element"]
    assert finding.data_location == case["xml_path_context"]
    assert finding.severity == Severity.FATAL
    assert finding.violation_kind == "MissingRequiredValue"


@pytest.mark.parametrize(
    "case",
    CASES,
    ids=lambda case: f"{case['row_id']}-{case['rule_id']}",
)
def test_it_33_r5_s1_executable_expectations(case):
    """Prove expectations reject absent behavior and accept real findings."""
    root = ET.parse(FIXTURES / "tests" / case["filename"]).getroot()
    lookup_path = "." + case["xml_path_context"]
    parent_path = lookup_path.rsplit("/", 1)[0]

    # Establish valid test setup before testing missing behavior.
    assert len(root.findall(parent_path, required_data.NS)) == 1
    assert root.findall(lookup_path, required_data.NS) == []

    # An evaluator that produces no findings must fail this expectation.
    # This is a deliberate sensitivity check, not historical RED evidence.
    with pytest.raises(
        AssertionError,
        match="Expected one required-data finding",
    ):
        assert_expected_finding([], case)

    required_data.load_required_rules.cache_clear()
    try:
        findings = required_data.evaluate_required_data(root, Investor.BOTH)
        assert_expected_finding(findings, case)
    finally:
        required_data.load_required_rules.cache_clear()