"""Reconcile UAD1279 evaluation with the configured published workbook."""

from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from app.models.enums import Investor
from app.services import required_structure_required_data as service
from app.services.gse_constraint_sources import (
    read_active_compliance_workbook_rows,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIGURATION = ROOT / "config" / "configuration.ttl"
RULE_ID = "UAD1279"
XML_NAMESPACE = "http://www.mismo.org/residential/2009/schemas"


@pytest.fixture(scope="module")
def governed_row():
    """Use the published workbook, never a CSV-derived rule row."""
    source = read_active_compliance_workbook_rows(
        configuration_path=CONFIGURATION,
    )
    matches = [
        dict(row)
        for row in source.rows
        if row.get("Message ID") == RULE_ID
    ]
    assert len(matches) == 1, (
        "The configured workbook must contain exactly one UAD1279 row."
    )

    row = matches[0]
    row["_source_document"] = str(source.workbook_path)
    row["_source_sheet"] = source.worksheet_name
    return row


def _element(parent, name, text=None):
    node = ET.SubElement(
        parent,
        f"{{{XML_NAMESPACE}}}{name}",
    )
    if text is not None:
        node.text = text
    return node


def _property(
    properties,
    *,
    valuation_use,
    method,
    new_construction,
    rooms,
):
    prop = _element(properties, "PROPERTY")
    prop.set("ValuationUseType", valuation_use)

    detail = _element(prop, "PROPERTY_DETAIL")
    _element(
        detail,
        "NewConstructionIndicator",
        new_construction,
    )

    valuations = _element(prop, "PROPERTY_VALUATIONS")
    valuation = _element(valuations, "PROPERTY_VALUATION")
    valuation_detail = _element(
        valuation,
        "PROPERTY_VALUATION_DETAIL",
    )
    _element(
        valuation_detail,
        "PropertyValuationMethodType",
        method,
    )

    improvements = _element(prop, "IMPROVEMENTS")
    improvement = _element(improvements, "IMPROVEMENT")
    units = _element(improvement, "PROPERTY_UNITS")
    unit = _element(units, "PROPERTY_UNIT")
    room_collection = _element(unit, "ROOMS")

    for room_type, has_photo in rooms:
        room = _element(room_collection, "ROOM")
        room_detail = _element(room, "ROOM_DETAIL")
        _element(room_detail, "RoomType", room_type)

        if has_photo:
            images = _element(room, "IMAGES")
            _element(images, "IMAGE")

    return prop


def _report(
    *,
    method="TraditionalAppraisal",
    new_construction="false",
    conclusion="SubjectToRepair",
    rooms=(("Kitchen", False),),
    comparable_rooms=None,
):
    analysis = ET.Element(
        f"{{{XML_NAMESPACE}}}VALUATION_ANALYSIS"
    )
    properties = _element(analysis, "PROPERTIES")

    _property(
        properties,
        valuation_use="SubjectProperty",
        method=method,
        new_construction=new_construction,
        rooms=rooms,
    )

    if comparable_rooms is not None:
        _property(
            properties,
            valuation_use="SalesComparable",
            method=method,
            new_construction=new_construction,
            rooms=comparable_rooms,
        )

    reconciliation = _element(
        analysis,
        "VALUATION_RECONCILIATION",
    )
    summary = _element(
        reconciliation,
        "VALUATION_RECONCILIATION_SUMMARY",
    )
    conditions = _element(summary, "VALUATION_CONDITIONS")
    condition = _element(conditions, "VALUATION_CONDITION")
    _element(
        condition,
        "PropertyValuationConditionalConclusionType",
        conclusion,
    )
    return analysis


def _evaluate(governed_row, document):
    before = ET.tostring(document)
    findings = service.evaluate_required_structure(
        document,
        Investor.BOTH,
        governed_row,
    )
    assert ET.tostring(document) == before, (
        "Evaluation must not modify the submitted XML."
    )
    assert all(
        finding.rule_id == RULE_ID
        for finding in findings
    )
    return findings


def test_uad1279_binding_matches_published_workbook(governed_row):
    binding = service.load_bindings().get(RULE_ID)
    assert binding is not None
    assert binding["sourceFingerprint"] == service.fingerprint(
        governed_row
    ), (
        "UAD1279's binding must match the reviewed published workbook "
        "definition. Updating the fingerprint also requires reconciling "
        "the evaluator's governed behavior."
    )


@pytest.mark.parametrize(
    "method,new_construction,conclusion,expected_count",
    [
        (
            "TraditionalAppraisal",
            "false",
            "SubjectToRepair",
            1,
        ),
        (
            "TraditionalAppraisal",
            "false",
            "SubjectToCompletionPerPlans",
            1,
        ),
        (
            "TraditionalAppraisal",
            "true",
            "SubjectToRepair",
            1,
        ),
        (
            "TraditionalAppraisal",
            "true",
            "SubjectToCompletionPerPlans",
            0,
        ),
        (
            "ExteriorAppraisal",
            "false",
            "SubjectToRepair",
            0,
        ),
        (
            "ExteriorAppraisal",
            "false",
            "SubjectToCompletionPerPlans",
            0,
        ),
        (
            "ExteriorAppraisal",
            "true",
            "SubjectToRepair",
            0,
        ),
        (
            "ExteriorAppraisal",
            "true",
            "SubjectToCompletionPerPlans",
            0,
        ),
    ],
)
def test_uad1279_obeys_published_applicability_conditions(
    governed_row,
    method,
    new_construction,
    conclusion,
    expected_count,
):
    findings = _evaluate(
        governed_row,
        _report(
            method=method,
            new_construction=new_construction,
            conclusion=conclusion,
        ),
    )
    assert len(findings) == expected_count


@pytest.mark.parametrize(
    "room_type",
    ("Kitchen", "HalfBathroom", "FullBathroom"),
)
@pytest.mark.parametrize("has_photo", (False, True))
def test_uad1279_requires_a_photo_in_each_mandatory_room(
    governed_row,
    room_type,
    has_photo,
):
    findings = _evaluate(
        governed_row,
        _report(rooms=((room_type, has_photo),)),
    )
    assert len(findings) == (0 if has_photo else 1)


@pytest.mark.parametrize(
    "first_photo,second_photo,expected_count",
    [
        (False, False, 2),
        (True, False, 1),
        (False, True, 1),
        (True, True, 0),
    ],
)
def test_uad1279_checks_each_room_independently(
    governed_row,
    first_photo,
    second_photo,
    expected_count,
):
    findings = _evaluate(
        governed_row,
        _report(
            rooms=(
                ("Kitchen", first_photo),
                ("FullBathroom", second_photo),
            ),
        ),
    )
    assert len(findings) == expected_count


def test_uad1279_does_not_require_a_photo_for_an_unlisted_room(
    governed_row,
):
    findings = _evaluate(
        governed_row,
        _report(rooms=(("Bedroom", False),)),
    )
    assert findings == []


def test_uad1279_comparable_photo_does_not_satisfy_subject_requirement(
    governed_row,
):
    findings = _evaluate(
        governed_row,
        _report(
            rooms=(("Kitchen", False),),
            comparable_rooms=(("Kitchen", True),),
        ),
    )
    assert len(findings) == 1


def test_uad1279_missing_comparable_photo_does_not_fail_subject(
    governed_row,
):
    findings = _evaluate(
        governed_row,
        _report(
            rooms=(("Kitchen", True),),
            comparable_rooms=(("Kitchen", False),),
        ),
    )
    assert findings == []


def test_uad1279_still_rejects_unreviewed_source_changes(
    governed_row,
):
    changed_row = dict(governed_row)
    changed_row["Rule Logic"] += " UNREVIEWED TEST CHANGE"

    with pytest.raises(
        ValueError,
        match="governed required-structure definition changed",
    ):
        service.binding_for(changed_row)


def test_uad1279_findings_preserve_published_source_values(
    governed_row,
):
    findings = _evaluate(
        governed_row,
        _report(),
    )
    assert len(findings) == 1

    finding = findings[0]
    assert finding.row_id == governed_row["Unique ID"]
    assert finding.finding == governed_row["Message Text"]
    assert finding.expected_condition == governed_row["Rule Logic"]
    assert finding.property_affected == governed_row["Property Affected"]
    assert finding.source is not None
    assert (
        finding.source.source_document
        == governed_row["_source_document"]
    )
    assert (
        finding.source.source_sheet
        == governed_row["_source_sheet"]
    )
    assert (
        finding.source.source_section
        == governed_row["Unique ID"]
    )