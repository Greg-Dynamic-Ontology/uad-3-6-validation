"""IT-33R4S1: produce an actionable finding for missing required data."""

import csv
from pathlib import Path
from xml.etree import ElementTree as ET

from app.models.enums import Investor, RuleType, Severity
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


def test_it_33_r4_s1_actionable_required_data_finding(
    required_data_baseline_clock,
):
    """Return a deterministic finding traceable to its workbook source."""
    required_data.load_required_rules.cache_clear()

    try:
        loaded = required_data.load_required_rules()
        rows = [
            row for row in loaded
            if row["Unique ID"] == "0100.0007"
            and row["Message ID"] == "UAD1001"
        ]
        assert len(rows) == 1, (
            "The production workbook loader must supply governed row "
            "0100.0007 / UAD1001 exactly once."
        )
        rule = rows[0]

        with (FIXTURES / "manifest.csv").open(
            encoding="utf-8-sig", newline=""
        ) as stream:
            cases = [
                case for case in csv.DictReader(stream)
                if case["row_id"] == "0100.0007"
            ]

        assert len(cases) == 1, (
            "Test setup requires one matching fixture."
        )
        case = cases[0]
        assert case["rule_id"] == rule["Message ID"]

        fixture_path = FIXTURES / "tests" / case["filename"]
        original = fixture_path.read_bytes()
        root = ET.fromstring(original)
        original_tree = ET.tostring(root)

        # Exercise the real production loader and all loaded evaluators.
        findings = required_data.evaluate_required_data(
            root, Investor.BOTH
        )

        assert len(findings) == 1
        finding = findings[0]

        # Governed identities remain distinct from generated finding IDs.
        assert finding.row_id == "0100.0007"
        assert finding.rule_id == rule["Message ID"]
        assert finding.row_id != case["filename"]
        assert finding.row_id != finding.finding_id

        # Identify the deficient context and explain the correction.
        assert finding.data_location == case["xml_path_context"]
        assert finding.severity == Severity.FATAL
        assert finding.rule_type == RuleType.APPENDIX_H
        assert finding.finding == rule["Message Text"]
        assert finding.expected_condition == (
            f"{rule['Primary Data Element']} must be provided."
        )

        # Preserve traceability to the actual workbook and worksheet.
        assert rule["_source_document"]
        assert rule["_source_sheet"]
        assert finding.source is not None
        assert finding.source.source_document == rule["_source_document"]
        assert finding.source.source_sheet == rule["_source_sheet"]
        assert finding.source.source_version == "UAD 3.6"
        assert finding.source.source_section == rule["Unique ID"]

        # Expose governed meaning explicitly in the serialized finding.
        payload = finding.model_dump()
        expected = {
            "primary_data_element": rule["Primary Data Element"],
            "property_affected": rule["Property Affected"],
            "violation_kind": "MissingRequiredValue",
        }
        actual = {name: payload.get(name) for name in expected}

        assert actual == expected, (
            "The finding must explicitly identify the governed element, "
            f"property scope, and violation kind. Received: {actual}"
        )

        assert ET.tostring(root) == original_tree
        assert fixture_path.read_bytes() == original
    finally:
        required_data.load_required_rules.cache_clear()