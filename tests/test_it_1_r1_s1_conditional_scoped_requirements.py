"""IT-1R1S1: Test conditional and scoped requirements.

Load standalone XML cases and expectations from manifest.ttl.
Do not construct appraisal XML or implement applicability logic here.
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
CASE_DIRECTORY = ROOT / "tests" / "fixtures" / "it_1" / "r1" / "s1"
MANIFEST = CASE_DIRECTORY / "manifest.ttl"
INVENTORY = ROOT / "data" / "spreadsheet-rule-category-tracking.ttl"

TRACKING = Namespace("urn:uad36:work-tracking:vocab:")
SCENARIO = Namespace("urn:uad36:work-tracking:scenario:")
M = Namespace("urn:uad36:test-manifest:vocab:")

R1 = Namespace("urn:uad36:work-tracking:r1-classification:")
SCHEMA = ROOT / (
    "chatgpt-sources/sources/schemas/UAD/GSE_UAD_3.6.0_v1.3/Combined/GSE_UAD_3.6.0_v1.3.xsd"
)
NS = {"m": "http://www.mismo.org/residential/2009/schemas"}
PRIOR_RULE_IDS = ("UAD1021", "UAD1024", "UAD1054")
SLICE_02_RULE_IDS = (
    "UAD1094", "UAD1100", "UAD1101", "UAD1147", "UAD1156",
    "UAD1294", "UAD1298", "UAD1330", "UAD1556", "UAD1568",
    "UAD1573", "UAD1578", "UAD1613", "UAD1629", "UAD1630",
    "UAD1632", "UAD1634", "UAD1635", "UAD1639", "UAD1642",
    "UAD1643", "UAD1645", "UAD1647", "UAD1664", "UAD1665",
    "UAD1669", "UAD1671", "UAD1672", "UAD1673", "UAD1687",
)
SOURCE_RULE_IDS = PRIOR_RULE_IDS + SLICE_02_RULE_IDS
STATES = {"not_applicable", "applicable_missing", "applicable_supplied"}

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
    """Require exactly one value rather than silently choosing one."""
    values = list(graph.objects(subject, predicate))
    assert len(values) == 1, (
        f"Manifest/source setup error: expected one {predicate} "
        f"on {subject}; found {len(values)}."
    )
    return values[0]


def text(graph, subject, predicate):
    value = single(graph, subject, predicate)
    assert isinstance(value, Literal), (
        f"Expected a literal for {predicate} on {subject}."
    )
    return str(value)


def nonnegative_integer(graph, subject, predicate):
    value = single(graph, subject, predicate)
    assert isinstance(value, Literal)
    number = value.toPython()
    assert type(number) is int and number >= 0, (
        f"Expected a nonnegative integer for {predicate} on {subject}."
    )
    return number


@lru_cache(maxsize=1)
def read_corpus():
    """Read RDF cases and check manifest structure."""
    assert MANIFEST.is_file(), (
        f"Test setup incomplete: save {MANIFEST}. "
        "This is not a behavioral RED result."
    )
    graph = Graph().parse(MANIFEST, format="turtle")
    manifests = list(graph.subjects(RDF.type, M.Manifest))
    assert len(manifests) == 1
    manifest = manifests[0]

    assert text(graph, manifest, M.scenarioId) == "IT-1R1S1"
    assert nonnegative_integer(graph, manifest, M.schemaVersion) == 1

    case_nodes = list(graph.objects(manifest, M.case))
    assert case_nodes, "The manifest must contain executable cases."
    assert set(case_nodes) == set(graph.subjects(RDF.type, M.TestCase)), (
        "Every TestCase must belong to this manifest."
    )

    assert nonnegative_integer(graph, manifest, M.caseCount) == 350
    assert len(case_nodes) == 350, "Expected 17 prior and 333 slice-02 cases."
    schema_node = single(graph, manifest, M.validationSchema)
    assert text(graph, schema_node, M.path) == SCHEMA.relative_to(ROOT).as_posix()
    assert text(graph, schema_node, M.sha256) == hashlib.sha256(
        SCHEMA.read_bytes()
    ).hexdigest(), "Validation schema changed; review fixture compatibility."

    cases = []
    for node in case_nodes:
        checks = []
        for check in graph.objects(node, M.fixtureCheck):
            item = {
                "path": text(graph, check, M.path),
                "count": nonnegative_integer(graph, check, M["count"]),
            }
            texts = list(graph.objects(check, M.expectedText))
            assert len(texts) <= 1
            if texts:
                assert isinstance(texts[0], Literal)
                assert item["count"] == 1, (
                    "An expectedText check must identify exactly one node."
                )
                item["texts"] = [str(texts[0])]
            checks.append(item)

        expected = []
        for finding in graph.objects(node, M.expectedFinding):
            expected.append({
                "rule_id": text(graph, finding, M.ruleId),
                "severity": text(graph, finding, M.severity),
                "data_location": text(graph, finding, M.dataLocation),
                "violation_kind": text(graph, finding, M.violationKind),
            })

        expected_count = nonnegative_integer(
            graph, node, M.expectedFindingCount
        )
        assert len(expected) == expected_count, (
            f"{node}: expectedFindingCount disagrees with RDF findings."
        )

        case = {
            "case_id": text(graph, node, M.caseId),
            "slice_id": text(graph, node, M.sliceId),
            "source_logic": text(graph, node, M.sourceRuleLogic),
            "rule_id": text(graph, node, M.ruleId),
            "source_row": nonnegative_integer(graph, node, M.sourceRow),
            "source_unique_id": text(graph, node, M.sourceUniqueId),
            "state": text(graph, node, M.state),
            "xml_file": text(graph, node, M.xmlFile),
            "xml_sha256": text(graph, node, M.xmlSha256),
            "fixture_checks": checks,
            "expected_findings": expected,
        }
        assert case["state"] in STATES
        expected_slice = "01" if case["rule_id"] in PRIOR_RULE_IDS else "02"
        assert case["slice_id"] == expected_slice
        assert bool(expected) == (case["state"] == "applicable_missing")
        assert checks, f"{case['case_id']}: missing fixture checks."
        cases.append(case)

    case_ids = [case["case_id"] for case in cases]
    assert len(case_ids) == len(set(case_ids)), "Duplicate case IDs."
    assert {case["rule_id"] for case in cases} == set(SOURCE_RULE_IDS)
    filenames = [case["xml_file"] for case in cases]
    assert len(filenames) == len(set(filenames)), "Duplicate XML filenames."
    assert Counter(case["slice_id"] for case in cases) == {"01": 17, "02": 333}
    for rule_id in SOURCE_RULE_IDS:
        assert {
            case["state"] for case in cases if case["rule_id"] == rule_id
        } == STATES, f"Missing Scenario state for {rule_id}."
    return tuple(sorted(cases, key=lambda case: case["case_id"]))


@pytest.fixture(scope="module")
def governed_rules():
    """Verify selected source rows and their R1 category membership."""
    graph = Graph().parse(INVENTORY, format="turtle")
    members = set(
        graph.objects(
            SCENARIO.other_conditional_scoped,
            TRACKING.coversRule,
        )
    )

    proposed = set(graph.objects(R1.nextSlice, TRACKING.proposedSliceRule))
    assert proposed <= members
    assert len(proposed) == 30
    assert {
        text(graph, subject, TRACKING.ruleId) for subject in proposed
    } == set(SLICE_02_RULE_IDS), "Test selection differs from the reviewed TTL."

    with required_data.RULE_FILE.open(
        encoding="utf-8-sig", newline=""
    ) as stream:
        reader = csv.DictReader(stream)
        fieldnames = reader.fieldnames
        rows = list(reader)

    selected = {}
    for rule_id in SOURCE_RULE_IDS:
        matches = [row for row in rows if row["Message ID"] == rule_id]
        assert len(matches) == 1, (
            f"Test setup requires exactly one CSV row for {rule_id}."
        )
        row = matches[0]

        subjects = [
            subject
            for subject in members
            if str(graph.value(subject, TRACKING.ruleId)) == rule_id
        ]
        assert len(subjects) == 1, (
            f"{rule_id} must belong to the governed R1 category."
        )
        subject = subjects[0]

        for column, predicate in SOURCE_FIELDS.items():
            assert row[column] == text(graph, subject, predicate), (
                f"{rule_id}: CSV and TTL disagree on {column}. "
                "Resolve the source discrepancy before evaluating RED."
            )

        selected[rule_id] = {
            "row": row,
            "source_row": nonnegative_integer(
                graph, subject, TRACKING.sourceRow
            ),
        }

    return fieldnames, selected


@pytest.fixture(scope="module")
def validation_schema():
    parser = XSD_ET.XMLParser(resolve_entities=False, no_network=True)
    return XSD_ET.XMLSchema(XSD_ET.parse(str(SCHEMA), parser))


def load_case_xml(case, validation_schema):
    """Check saved input and fixture facts before validation."""
    path = (CASE_DIRECTORY / case["xml_file"]).resolve()
    assert path.is_relative_to(CASE_DIRECTORY.resolve())
    assert path.is_file(), f"Missing fixture: {path}"

    content = path.read_bytes()
    assert hashlib.sha256(content).hexdigest() == case["xml_sha256"], (
        f"{case['case_id']}: XML differs from the reviewed manifest."
    )
    parser = XSD_ET.XMLParser(resolve_entities=False, no_network=True)
    schema_root = XSD_ET.fromstring(content, parser)
    assert validation_schema.validate(schema_root), (
        f"{case['case_id']}: fixture is not XSD-valid; not behavioral RED.\n"
        f"{validation_schema.error_log}"
    )
    root = ET.fromstring(content)

    checks = case["fixture_checks"]
    assert checks, f"{case['case_id']}: fixture checks are required."
    for check in checks:
        nodes = root.findall(check["path"], NS)
        assert len(nodes) == check["count"], (
            f"{case['case_id']}: unexpected node count at "
            f"{check['path']}"
        )
        if "texts" in check:
            assert [node.text for node in nodes] == check["texts"], (
                f"{case['case_id']}: unexpected fixture values at "
                f"{check['path']}"
            )

    for finding in case["expected_findings"]:
        location = finding["data_location"]
        assert location.startswith("//m:VALUATION_ANALYSIS/")
        lookup = "." + location
        assert len(root.findall(lookup.rsplit("/", 1)[0], NS)) == 1, (
            f"{case['case_id']}: expected finding lacks a unique XML context."
        )
        assert root.findall(lookup, NS) == [], (
            f"{case['case_id']}: expected missing dependent element is present."
        )
    return path, content, root


def assert_case(case, rule, findings):
    """Compare complete observable outcomes with manifest expectations."""
    expected = case["expected_findings"]
    expected_severity = Severity(rule["Severity"].casefold())

    for item in expected:
        assert item["rule_id"] == rule["Message ID"]
        assert item["severity"] == expected_severity.value
        assert item["violation_kind"] == "MissingRequiredValue"

    actual_outcomes = Counter(
        (
            finding.rule_id,
            finding.severity.value,
            finding.data_location,
            finding.violation_kind,
        )
        for finding in findings
    )
    expected_outcomes = Counter(
        (
            item["rule_id"],
            item["severity"],
            item["data_location"],
            item["violation_kind"],
        )
        for item in expected
    )
    assert actual_outcomes == expected_outcomes, (
        f"{case['case_id']}: findings differ from the expected "
        f"rule, severity, XML context, or violation kind.\n"
        f"Expected: {expected_outcomes}\n"
        f"Actual: {actual_outcomes}"
    )

    for finding in findings:
        assert finding.row_id == rule["Unique ID"]
        assert finding.rule_type == RuleType.APPENDIX_H
        assert finding.primary_data_element == rule["Primary Data Element"]
        assert finding.property_affected == rule["Property Affected"]
        assert finding.finding == rule["Message Text"]
        assert finding.source is not None
        assert finding.source.source_section == rule["Unique ID"]


@pytest.mark.parametrize(
    "case",
    read_corpus(),
    ids=lambda case: f"slice-{case['slice_id']}-{case['case_id']}",
)
def test_it_1_r1_s1_conditional_scoped_requirement(
    case, governed_rules, validation_schema, tmp_path, monkeypatch
):
    """Report each saved XML case independently, including prior coverage."""
    fieldnames, selected = governed_rules
    source = selected[case["rule_id"]]
    rule = source["row"]
    assert case["source_row"] == source["source_row"]
    assert case["source_unique_id"] == rule["Unique ID"]
    assert case["source_logic"] == rule["Rule Logic"]

    path, original_bytes, root = load_case_xml(case, validation_schema)
    original_tree = ET.tostring(root)

    # Use the production loader; do not bypass its selection behavior.
    inventory = tmp_path / "selected-rules.csv"
    with inventory.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(rule)

    monkeypatch.setattr(required_data, "RULE_FILE", inventory)
    required_data.load_required_rules.cache_clear()
    try:
        findings = required_data.evaluate_required_data(root, Investor.BOTH)
        assert ET.tostring(root) == original_tree, (
            f"{case['case_id']}: validation changed the XML tree."
        )
        assert path.read_bytes() == original_bytes, (
            f"{case['case_id']}: validation changed the saved fixture."
        )
        assert_case(case, rule, findings)
    finally:
        required_data.load_required_rules.cache_clear()