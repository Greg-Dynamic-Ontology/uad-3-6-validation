"""IT-1R1S2 RED tests for correlated, per-instance requirements.

Cases and expected outcomes are reviewed XML fixtures in manifest.ttl. This
runner does not build XML or implement rule applicability.
"""

import csv
import hashlib
from collections import Counter
from functools import lru_cache
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
from lxml import etree as XSD_ET
from rdflib import Graph, Literal, Namespace, RDF

from app.models.enums import Investor, RuleType, Severity
from app.services import required_data


ROOT = Path(__file__).resolve().parents[1]
CASE_DIRECTORY = ROOT / "tests" / "fixtures" / "it_1" / "r1" / "s2"
MANIFEST = CASE_DIRECTORY / "manifest.ttl"
INVENTORY = ROOT / "data" / "spreadsheet-rule-category-tracking.ttl"
TRACKING = Namespace("urn:uad36:work-tracking:vocab:")
BASE = Namespace("urn:uad36:work-tracking:")
SCENARIO = Namespace("urn:uad36:work-tracking:scenario:")
M = Namespace("urn:uad36:test-manifest:vocab:")
SCHEMA = ROOT / (
    "chatgpt-sources/sources/schemas/UAD/GSE_UAD_3.6.0_v1.3/Combined/"
    "GSE_UAD_3.6.0_v1.3.xsd"
)
NS = {"m": "http://www.mismo.org/residential/2009/schemas"}
FAMILY_RULES = {"UAD1055", "UAD1059", "UAD1083", "UAD1095", "UAD1096"}
SOURCE_FIELDS = {
    "Unique ID": TRACKING.sourceUniqueIdCell,
    "Primary Data Element": TRACKING.primaryDataElement,
    "Message ID": TRACKING.ruleId,
    "Message Text": TRACKING.messageText,
    "Rule Logic": TRACKING.ruleLogic,
    "Severity": TRACKING.severity,
    "Property Affected": TRACKING.propertyAffected,
    " xPath": TRACKING.xpath,
}


def single(graph, subject, predicate):
    values = list(graph.objects(subject, predicate))
    assert len(values) == 1, (
        f"Fixture/source setup error: expected one {predicate} on {subject}; "
        f"found {len(values)}. This is not behavioral RED."
    )
    return values[0]


def text(graph, subject, predicate):
    value = single(graph, subject, predicate)
    assert isinstance(value, Literal)
    return str(value)


def integer(graph, subject, predicate):
    value = single(graph, subject, predicate)
    assert isinstance(value, Literal)
    number = value.toPython()
    assert type(number) is int and number >= 0
    return number


@lru_cache(maxsize=1)
def read_corpus():
    assert MANIFEST.is_file(), (
        f"Fixture setup incomplete: save and generate {MANIFEST}; "
        "a missing manifest is not behavioral RED."
    )
    graph = Graph().parse(MANIFEST, format="turtle")
    manifests = list(graph.subjects(RDF.type, M.Manifest))
    assert len(manifests) == 1
    manifest = manifests[0]
    assert text(graph, manifest, M.scenarioId) == "IT-1R1S2"
    assert text(graph, manifest, M.fixtureFamily) == "outbuilding"
    cases = list(graph.objects(manifest, M.case))
    assert cases and set(cases) == set(graph.subjects(RDF.type, M.TestCase))
    rules = {text(graph, case, M.ruleId) for case in cases}
    assert rules == FAMILY_RULES, (
        "The outbuilding corpus must cover exactly its five reviewed rules; "
        "fixture selection is setup, not RED."
    )
    schema_node = single(graph, manifest, M.validationSchema)
    assert text(graph, schema_node, M.path) == SCHEMA.relative_to(ROOT).as_posix()
    assert text(graph, schema_node, M.sha256) == hashlib.sha256(
        SCHEMA.read_bytes()
    ).hexdigest(), "Schema changed; review fixtures before running RED."

    parsed = []
    for node in cases:
        checks = []
        for check in graph.objects(node, M.fixtureCheck):
            item = {
                "path": text(graph, check, M.path),
                "count": integer(graph, check, M["count"]),
            }
            expected_text = list(graph.objects(check, M.expectedText))
            assert len(expected_text) <= 1
            if expected_text:
                assert isinstance(expected_text[0], Literal)
                item["texts"] = [str(expected_text[0])]
            checks.append(item)
        findings = []
        for finding in graph.objects(node, M.expectedFinding):
            findings.append({
                "rule_id": text(graph, finding, M.ruleId),
                "severity": text(graph, finding, M.severity),
                "data_location": text(graph, finding, M.dataLocation),
                "violation_kind": text(graph, finding, M.violationKind),
            })
        expected_count = integer(graph, node, M.expectedFindingCount)
        assert len(findings) == expected_count
        item = {
            "case_id": text(graph, node, M.caseId),
            "rule_id": text(graph, node, M.ruleId),
            "source_row": integer(graph, node, M.sourceRow),
            "source_unique_id": text(graph, node, M.sourceUniqueId),
            "source_logic": text(graph, node, M.sourceRuleLogic),
            "state": text(graph, node, M.state),
            "xml_file": text(graph, node, M.xmlFile),
            "xml_sha256": text(graph, node, M.xmlSha256),
            "checks": checks,
            "findings": findings,
        }
        assert item["rule_id"] in FAMILY_RULES
        assert item["state"] in {"applicable_missing", "applicable_supplied", "not_applicable"}
        assert checks, f"{item['case_id']}: missing fixture integrity checks."
        parsed.append(item)
    ids = [item["case_id"] for item in parsed]
    files = [item["xml_file"] for item in parsed]
    assert len(ids) == len(set(ids)), "Duplicate manifest case IDs."
    assert len(files) == len(set(files)), "Duplicate fixture paths."
    for rule_id in FAMILY_RULES:
        rule_cases = [item for item in parsed if item["rule_id"] == rule_id]
        assert rule_cases, f"No outbuilding cases for {rule_id}."
        assert {item["state"] for item in rule_cases} == {
            "applicable_missing", "applicable_supplied", "not_applicable"
        }, f"Missing a required applicability state for {rule_id}."
    return tuple(sorted(parsed, key=lambda item: item["case_id"]))


@pytest.fixture(scope="module")
def source_rules():
    graph = Graph().parse(INVENTORY, format="turtle")
    scenario = SCENARIO.it_1_r1_s2
    members = set(graph.objects(scenario, TRACKING.coversRule))
    assert members, "IT-1R1S2 membership is absent from the saved tracker."
    selected_family = set(
        graph.subjects(TRACKING.fixtureFamily, BASE.fixtureFamilyOutbuilding)
    )
    selected_family_ids = {
        str(graph.value(subject, TRACKING.ruleId)) for subject in selected_family
    }
    assert selected_family_ids == FAMILY_RULES, (
        "The saved tracker’s outbuilding fixture-family membership changed."
    )
    members &= selected_family
    selected = {}
    with required_data.RULE_FILE.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        fieldnames, rows = reader.fieldnames, list(reader)
    assert fieldnames
    for rule_id in FAMILY_RULES:
        row_matches = [row for row in rows if row["Message ID"] == rule_id]
        assert len(row_matches) == 1, f"CSV must contain exactly one {rule_id}."
        subject_matches = [
            subject for subject in members
            if str(graph.value(subject, TRACKING.ruleId)) == rule_id
        ]
        assert len(subject_matches) == 1, f"Tracker must select {rule_id} once."
        subject = subject_matches[0]
        row = row_matches[0]
        for column, predicate in SOURCE_FIELDS.items():
            assert row[column] == text(graph, subject, predicate), (
                f"{rule_id}: CSV and tracker disagree on {column}; "
                "resolve source setup before evaluating RED."
            )
        selected[rule_id] = {
            "row": row,
            "source_row": integer(graph, subject, TRACKING.sourceRow),
        }
    return fieldnames, selected


@pytest.fixture(scope="module")
def validation_schema():
    parser = XSD_ET.XMLParser(resolve_entities=False, no_network=True)
    return XSD_ET.XMLSchema(XSD_ET.parse(str(SCHEMA), parser))


def prepare_case(case, schema):
    path = (CASE_DIRECTORY / case["xml_file"]).resolve()
    assert path.is_relative_to(CASE_DIRECTORY.resolve()) and path.is_file(), (
        f"Missing/out-of-corpus fixture for {case['case_id']}; not RED."
    )
    original = path.read_bytes()
    assert hashlib.sha256(original).hexdigest() == case["xml_sha256"], (
        f"{case['case_id']}: fixture differs from reviewed manifest; not RED."
    )
    parser = XSD_ET.XMLParser(resolve_entities=False, no_network=True)
    root_xsd = XSD_ET.fromstring(original, parser)
    assert schema.validate(root_xsd), (
        f"{case['case_id']}: fixture is not schema-valid; not behavioral RED.\n"
        f"{schema.error_log}"
    )
    root = ET.fromstring(original)
    for check in case["checks"]:
        nodes = root.findall(check["path"], NS)
        assert len(nodes) == check["count"], (
            f"{case['case_id']}: fixture structure differs at {check['path']}."
        )
        if "texts" in check:
            assert [node.text for node in nodes] == check["texts"]
    for expected in case["findings"]:
        location = expected["data_location"]
        assert location.startswith("//m:VALUATION_ANALYSIS/")
        assert root.findall("." + location, NS) == [], (
            f"{case['case_id']}: expected missing element is present."
        )
    return path, original, root


def assert_findings(case, rule, findings):
    for item in case["findings"]:
        assert item["rule_id"] == rule["Message ID"]
        assert item["severity"] == Severity(rule["Severity"].casefold()).value
        assert item["violation_kind"] == "MissingRequiredValue"
    expected = Counter((x["rule_id"], x["severity"], x["data_location"], x["violation_kind"]) for x in case["findings"])
    actual = Counter((f.rule_id, f.severity.value, f.data_location, f.violation_kind) for f in findings)
    assert actual == expected, (
        f"{case['case_id']}: expected per-instance findings differ.\n"
        f"Expected: {expected}\nActual: {actual}"
    )
    for finding in findings:
        assert finding.row_id == rule["Unique ID"]
        assert finding.rule_type == RuleType.APPENDIX_H
        assert finding.primary_data_element == rule["Primary Data Element"]
        assert finding.property_affected == rule["Property Affected"]
        assert finding.finding == rule["Message Text"]
        assert finding.source is not None
        assert finding.source.source_section == rule["Unique ID"]


@pytest.mark.parametrize("case", read_corpus(), ids=lambda case: case["case_id"])
def test_it_1_r1_s2_outbuilding_correlated_instance_requirement(
    case, source_rules, validation_schema, tmp_path, monkeypatch
):
    """Each owner instance is evaluated independently against its own inputs."""
    fieldnames, selected = source_rules
    source = selected[case["rule_id"]]
    rule = source["row"]
    assert case["source_row"] == source["source_row"]
    assert case["source_unique_id"] == rule["Unique ID"]
    assert case["source_logic"] == rule["Rule Logic"]
    path, original_bytes, root = prepare_case(case, validation_schema)
    original_tree = ET.tostring(root)

    # Retain the production CSV loader so this slice exercises real selection.
    one_rule_csv = tmp_path / "outbuilding-rule.csv"
    with one_rule_csv.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(rule)
    monkeypatch.setattr(required_data, "RULE_FILE", one_rule_csv)
    required_data.load_required_rules.cache_clear()
    try:
        findings = required_data.evaluate_required_data(root, Investor.BOTH)
        assert ET.tostring(root) == original_tree, "Validation mutated the XML tree."
        assert path.read_bytes() == original_bytes, "Validation changed the fixture file."
        assert_findings(case, rule, findings)
    finally:
        required_data.load_required_rules.cache_clear()




