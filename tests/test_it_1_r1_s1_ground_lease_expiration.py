"""IT-1R1S1: UAD1025 ground-lease expiration requirement.

Preserve the five reviewed cases and existing saved UAD1024 fixtures.
Read governed source values from the configured published workbook.
Only the supplied-date case adds an element, in memory.
"""

from pathlib import Path
from xml.etree import ElementTree as ET

import app
import pytest
from lxml import etree
from rdflib import Graph, Namespace, RDF

from app.models.enums import Investor, RuleType, Severity
from app.services import required_data
from app.services.gse_constraint_sources import (
    read_active_compliance_workbook_rows,
)


ROOT = Path(app.__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures/it_1/r1/s1/UAD1024"
TRACKER = ROOT / "data/spreadsheet-rule-category-tracking.ttl"
SCHEMA = ROOT / (
    "chatgpt-sources/sources/schemas/UAD/GSE_UAD_3.6.0_v1.3/"
    "Combined/GSE_UAD_3.6.0_v1.3.xsd"
)
NS = {"m": "http://www.mismo.org/residential/2009/schemas"}
M = Namespace("urn:uad36:test-manifest:vocab:")
T = Namespace("urn:uad36:work-tracking:vocab:")
SCENARIO = Namespace("urn:uad36:work-tracking:scenario:")
RULE_ID = "UAD1025"
ELEMENT = "PropertyGroundLeaseExpirationDate"
LOCATION = (
    "//m:VALUATION_ANALYSIS/m:PROPERTIES/"
    "m:PROPERTY[@ValuationUseType='SubjectProperty']/"
    "m:PROPERTY_GROUND_RENT/m:PropertyGroundLeaseExpirationDate"
)

CASES_TTL = """
@prefix m: <urn:uad36:test-manifest:vocab:> .
@prefix c: <urn:uad36:test-case:IT-1R1S1:UAD1025:> .

c:neither-condition a m:TestCase ;
    m:xmlFile "neither-missing.xml" ;
    m:estate "FeeSimple" ; m:commonLand "true" ;
    m:expectedCount 0 .
c:leasehold-only a m:TestCase ;
    m:xmlFile "left-only-missing.xml" ;
    m:estate "Leasehold" ; m:commonLand "true" ;
    m:expectedCount 0 .
c:noncommon-land-only a m:TestCase ;
    m:xmlFile "right-only-missing.xml" ;
    m:estate "FeeSimple" ; m:commonLand "false" ;
    m:expectedCount 0 .
c:applicable-missing a m:TestCase ;
    m:xmlFile "both-missing.xml" ;
    m:estate "Leasehold" ; m:commonLand "false" ;
    m:expectedCount 1 .
c:applicable-supplied a m:TestCase ;
    m:xmlFile "both-missing.xml" ;
    m:estate "Leasehold" ; m:commonLand "false" ;
    m:suppliedDate "2035-12-31" ; m:expectedCount 0 .
"""


def cases():
    graph = Graph().parse(data=CASES_TTL, format="turtle")
    result = []
    for node in sorted(graph.subjects(RDF.type, M.TestCase), key=str):
        supplied_date = graph.value(node, M.suppliedDate)
        result.append({
            "id": str(node).rsplit(":", 1)[-1],
            "file": str(graph.value(node, M.xmlFile)),
            "estate": str(graph.value(node, M.estate)),
            "common_land": str(graph.value(node, M.commonLand)),
            "date": (
                str(supplied_date)
                if supplied_date is not None
                else None
            ),
            "expected": int(graph.value(node, M.expectedCount)),
        })
    return result


@pytest.fixture(scope="module")
def source_rule():
    """Check workbook source identity and reviewed R1 membership."""
    workbook = read_active_compliance_workbook_rows(
        configuration_path=ROOT / "config" / "configuration.ttl",
    )
    matches = [
        row for row in workbook.rows
        if row["Message ID"] == RULE_ID
    ]
    assert len(matches) == 1
    row = {
        **matches[0],
        "_source_document": str(workbook.workbook_path),
        "_source_sheet": workbook.worksheet_name,
    }

    assert row["Unique ID"] == "0100.0029"
    assert row["Primary Data Element"] == ELEMENT
    assert row["Severity"] == "Fatal"
    assert row["Property Affected"] == "Subject"
    assert row["Rule Logic"] == (
        'If PropertyEstateType = "Leasehold" and '
        'LandOwnedInCommonIndicator = "false", and '
        "PropertyGroundLeaseExpirationDate is not provided"
    )
    assert row[" xPath"] == (
        "../VALUATION_ANALYSIS/PROPERTIES/PROPERTY/PROPERTY_GROUND_RENT/"
    )

    graph = Graph().parse(TRACKER, format="turtle")
    members = list(
        graph.objects(
            SCENARIO.other_conditional_scoped,
            T.coversRule,
        )
    )
    nodes = [
        node for node in members
        if str(graph.value(node, T.ruleId)) == RULE_ID
    ]
    assert len(nodes) == 1

    for column, predicate in {
        "Unique ID": T.sourceUniqueIdCell,
        "Primary Data Element": T.primaryDataElement,
        "Rule Logic": T.ruleLogic,
        "Severity": T.severity,
        "Property Affected": T.propertyAffected,
        " xPath": T.xpath,
    }.items():
        assert str(graph.value(nodes[0], predicate)) == row[column], (
            f"{RULE_ID}: tracker and published workbook disagree "
            f"on {column}."
        )

    return row


@pytest.fixture(scope="module")
def schema():
    parser = etree.XMLParser(resolve_entities=False, no_network=True)
    return etree.XMLSchema(etree.parse(str(SCHEMA), parser))


@pytest.mark.parametrize(
    "case",
    cases(),
    ids=lambda case: "UAD1025-" + case["id"],
)
def test_it_1_r1_s1_ground_lease_expiration(
    case, source_rule, schema, monkeypatch
):
    rule = source_rule
    path = FIXTURES / case["file"]
    original = path.read_bytes()
    root = ET.fromstring(original)

    properties = root.findall(
        ".//m:VALUATION_ANALYSIS/m:PROPERTIES/"
        "m:PROPERTY[@ValuationUseType='SubjectProperty']",
        NS,
    )
    assert len(properties) == 1
    subject = properties[0]
    assert subject.findtext(
        "m:PROPERTY_DETAIL/m:PropertyEstateType",
        namespaces=NS,
    ) == case["estate"]

    common = subject.findall(".//m:LandOwnedInCommonIndicator", NS)
    assert len(common) == 1
    assert common[0].text == case["common_land"]

    parents = subject.findall("m:PROPERTY_GROUND_RENT", NS)
    assert len(parents) == 1
    assert parents[0].find("m:" + ELEMENT, NS) is None

    if case["date"] is not None:
        ET.SubElement(
            parents[0],
            "{" + NS["m"] + "}" + ELEMENT,
        ).text = case["date"]

    prepared = ET.tostring(root)
    schema.assertValid(etree.fromstring(prepared))

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

    assert ET.tostring(root) == prepared, (
        "Validation mutated the XML input."
    )
    assert path.read_bytes() == original, (
        "Saved baseline fixture changed."
    )
    assert len(findings) == case["expected"], (
        f"IT-1R1S1 / {RULE_ID} / {case['id']}: expected "
        f"{case['expected']} missing-data findings; "
        f"received {len(findings)}. "
        "Leasehold with land not owned in common requires an expiration date."
    )

    for finding in findings:
        assert finding.rule_id == RULE_ID
        assert finding.row_id == "0100.0029"
        assert finding.severity == Severity.FATAL
        assert finding.rule_type == RuleType.APPENDIX_H
        assert finding.primary_data_element == ELEMENT
        assert finding.property_affected == "Subject"
        assert finding.violation_kind == "MissingRequiredValue"
        assert finding.data_location == LOCATION
        assert finding.finding == rule["Message Text"]
        assert finding.source is not None
        assert finding.source.source_section == "0100.0029"