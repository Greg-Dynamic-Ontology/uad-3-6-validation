"""Reconcile UAD1455 with the configured published compliance workbook."""

from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from app.models.enums import Investor
from app.services import aggregate_cross_record_required_data as service
from app.services.gse_constraint_sources import (
    read_active_compliance_workbook_rows,
)


ROOT = Path(__file__).resolve().parents[1]
NS = "http://www.mismo.org/residential/2009/schemas"
ADJUSTABLE = "SalesComparableAdditionalAdjustableComparisonItem"
NONADJUSTABLE = "SalesComparableAdditionalNonAdjustableComparisonItem"
LABEL = "Below Grade Exterior Access"


@pytest.fixture(scope="module")
def governed_row():
    source = read_active_compliance_workbook_rows(
        configuration_path=ROOT / "config" / "configuration.ttl",
    )
    matches = [
        dict(row)
        for row in source.rows
        if row.get("Message ID") == "UAD1455"
    ]
    assert len(matches) == 1, (
        "The configured workbook must contain exactly one UAD1455 row."
    )
    row = matches[0]
    row["_source_document"] = str(source.workbook_path)
    row["_source_sheet"] = source.worksheet_name
    return row


def element(parent, name, text=None):
    node = ET.SubElement(parent, f"{{{NS}}}{name}")
    if text is not None:
        node.text = text
    return node


def report(subject_keys, comparable_keys, other_keys=None):
    """Create evaluator fragments, not complete schema-valid reports."""
    root = ET.Element(f"{{{NS}}}MESSAGE")
    analysis = element(root, "VALUATION_ANALYSIS")
    properties = element(analysis, "PROPERTIES")

    inventories = [
        ("SubjectProperty", subject_keys),
        ("SalesComparable", comparable_keys),
    ]
    if other_keys is not None:
        inventories.append(("GrossRentMultiplierComparable", other_keys))

    for role, keys in inventories:
        prop = element(properties, "PROPERTY")
        prop.set("ValuationUseType", role)
        comparable = element(prop, "COMPARABLE")
        adjustments = element(comparable, "COMPARABLE_ADJUSTMENTS")
        for adjustment_type, identifier in keys:
            adjustment = element(adjustments, "COMPARABLE_ADJUSTMENT")
            element(
                adjustment,
                "ComparableAdjustmentType",
                adjustment_type,
            )
            element(
                adjustment,
                "AdditionalComparisonLineItemIdentifier",
                identifier,
            )
    return root


@pytest.mark.parametrize(
    "subject_keys,comparable_keys,other_keys,expected_count",
    [
        (
            [(ADJUSTABLE, LABEL)],
            [(ADJUSTABLE, LABEL)],
            None,
            0,
        ),
        (
            [(ADJUSTABLE, LABEL)],
            [(ADJUSTABLE, "Different label")],
            None,
            1,
        ),
        (
            [(ADJUSTABLE, LABEL)],
            [],
            None,
            1,
        ),
        (
            [],
            [(ADJUSTABLE, LABEL)],
            None,
            1,
        ),
        (
            [(ADJUSTABLE, LABEL)],
            [(NONADJUSTABLE, LABEL)],
            None,
            1,
        ),
        (
            [(ADJUSTABLE, LABEL)],
            [(ADJUSTABLE, LABEL)],
            [(ADJUSTABLE, "Unrelated property label")],
            0,
        ),
    ],
    ids=[
        "matching-keys",
        "different-identifiers",
        "missing-comparable-row",
        "missing-subject-row",
        "different-adjustment-types",
        "unrelated-property-isolated",
    ],
)
def test_uad1455_compares_governed_row_keys(
    governed_row,
    subject_keys,
    comparable_keys,
    other_keys,
    expected_count,
):
    findings = service.evaluate_aggregate_cross_record(
        report(subject_keys, comparable_keys, other_keys),
        Investor.FANNIE_MAE,
        governed_row,
    )
    assert len(findings) == expected_count
    for finding in findings:
        assert finding.rule_id == governed_row["Message ID"]
        assert finding.expected_condition == governed_row["Rule Logic"]
        assert finding.finding == governed_row["Message Text"]


def test_uad1455_preserves_workbook_provenance(governed_row):
    findings = service.evaluate_aggregate_cross_record(
        report([(ADJUSTABLE, LABEL)], []),
        Investor.FANNIE_MAE,
        governed_row,
    )
    assert len(findings) == 1
    finding = findings[0]
    assert finding.row_id == governed_row["Unique ID"]
    assert finding.source.source_document == governed_row["_source_document"]
    assert finding.source.source_sheet == governed_row["_source_sheet"]


def test_uad1455_still_rejects_changed_governed_meaning(governed_row):
    changed = dict(governed_row)
    changed["Rule Logic"] += " Unreviewed change."
    with pytest.raises(
        ValueError,
        match="UAD1455: governed aggregate definition changed",
    ):
        service.binding_for(changed)