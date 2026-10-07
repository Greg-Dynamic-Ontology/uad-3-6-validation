"""IT-1R13S1: aggregate consistency using saved schema-valid XML and RDF.

Original CSV rows drive production. This runner never generates or modifies
the saved corpus and does not import the generator's fixture oracle.
"""

import csv
import hashlib
import json
from copy import deepcopy
from decimal import Decimal
from pathlib import Path, PurePosixPath
from xml.etree import ElementTree as ET

import app
import pytest
from lxml import etree
from rdflib import Graph, Literal, Namespace, RDF, URIRef

from app.models.enums import Investor, RuleType, Severity
from app.services import required_data


ROOT = Path(app.__file__).resolve().parents[1]
FIXTURES = "tests/fixtures/it_1/r13/s1"
T = Namespace("urn:uad36:test-suite:vocab:")
WT = Namespace("urn:uad36:work-tracking:vocab:")
SUITE = URIRef("urn:uad36:test-suite:aggregate-cross-record-consistency")
SCENARIO = URIRef("urn:uad36:work-tracking:scenario:aggregate_cross_record_consistency")
NS = {
    "m": "http://www.mismo.org/residential/2009/schemas",
    "xlink": "http://www.w3.org/1999/xlink",
}
FIELDS = {
    "Message ID": T.ruleId,
    "Unique ID": T.sourceUniqueIdCell,
    "Primary Data Element": T.primaryDataElement,
    "Rule Logic": T.ruleLogic,
    "Severity": T.severity,
    "Property Affected": T.propertyAffected,
    " xPath": T.xpath,
    "Message Text": T.messageText,
}
CROSS_RECORD_CASES = {
    "identifier-mismatch", "missing-comparable-row", "missing-subject-row",
    "extra-comparable-row", "type-and-identifier-key",
    "other-property-control", "separate-analysis-groups",
}
EXPECTED_CASES = {
    "UAD1011": {"zero-adus", "one-adu", "other-property-control"},
    "UAD1016": {
        "one-dwelling", "zero-dwellings", "exclude-outbuilding",
        "two-dwellings", "other-property-control",
    },
    "UAD1019": {"one-non-adu", "zero-non-adus", "other-property-control"},
    "UAD1086": {"one-unit", "local-improvement-count", "other-property-control"},
    "UAD1693": {"one-structure", "multiple-structures", "other-property-control"},
    "UAD1461": {
        "decimal-mixed-sign", "negative-total", "zero-total",
        "subject-adjustment-control",
    },
    "UAD1250": CROSS_RECORD_CASES,
    "UAD1455": CROSS_RECORD_CASES | {"nonadjustable-identifier-mismatch"},
}
CONTROLS = {
    (rule, "other-property-control") for rule in EXPECTED_CASES
    if rule != "UAD1461"
} | {("UAD1461", "subject-adjustment-control")}
SOURCE_IDS = {
    "UAD1011": "0100.0019", "UAD1016": "0100.0021",
    "UAD1019": "0100.0022", "UAD1086": "0300.0063",
    "UAD1250": "1200.0032", "UAD1455": "1800.0319",
    "UAD1461": "1800.0313", "UAD1693": "0300.0063",
}
SALES_TYPES = {
    "SalesComparableAdditionalAdjustableComparisonItem",
    "SalesComparableAdditionalNonAdjustableComparisonItem",
}
GRM_TYPE = "GrossRentMultiplierAdditionalNonAdjustableComparisonItem"


def value(graph, node, predicate, allow_blank=False):
    values = list(graph.objects(node, predicate))
    assert len(values) == 1, f"{node}: expected one {predicate}"
    assert isinstance(values[0], Literal), f"{node}: expected literal {predicate}"
    result = values[0].toPython()
    if isinstance(result, str):
        assert allow_blank or result.strip(), f"{node}: blank {predicate}"
    return result


def checked_path(relative, fixture=False):
    portable = PurePosixPath(relative)
    assert not portable.is_absolute() and ".." not in portable.parts
    assert "\\" not in relative and ":" not in relative
    path = (ROOT / portable).resolve()
    assert path.is_relative_to(ROOT.resolve()) and path.is_file()
    if fixture:
        assert path.is_relative_to((ROOT / FIXTURES).resolve())
    return path


def fingerprint(row):
    data = json.dumps(
        [row[column] for column in FIELDS],
        ensure_ascii=False, separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def load_inventory():
    graph = Graph().parse(ROOT / FIXTURES / "manifest.ttl", format="turtle")
    tracking = Graph().parse(ROOT / "data/spreadsheet-rule-category-tracking.ttl", format="turtle")
    cases = sorted(graph.objects(SUITE, T.hasCase), key=str)
    assert value(graph, SUITE, T.scenarioId) == "IT-1R13S1"
    assert value(graph, SUITE, T.generatedBy) == "scripts/testing/generate_it_1_r13_s1_fixtures.py"
    assert value(graph, SUITE, T.expectedCaseCount) == len(cases) == 36
    assert value(graph, SUITE, T.expectedFixtureCount) == 72
    assert value(graph, SUITE, T.sourceRuleCount) == 8
    assert set(graph.subjects(RDF.type, T.TestCase)) == set(cases)
    actual = [(value(graph, case, T.ruleId), value(graph, case, T.caseId)) for case in cases]
    expected = {(rule, name) for rule, names in EXPECTED_CASES.items() for name in names}
    assert len(actual) == len(set(actual)) and set(actual) == expected
    governed = set(tracking.objects(SCENARIO, WT.coversRule))
    assert len(governed) == 8
    assert {value(tracking, node, WT.ruleId) for node in governed} == set(EXPECTED_CASES)
    fixtures = []
    for case in cases:
        rule = value(graph, case, T.ruleId)
        assert value(graph, case, T.scenarioId) == "IT-1R13S1"
        assert value(graph, case, T.sourceUniqueIdCell) == SOURCE_IDS[rule]
        links = list(graph.objects(case, T.sourceRule))
        assert len(links) == 1 and links[0] in governed
        discrepancies = {}
        for node in graph.objects(case, T.sourceDiscrepancy):
            column = value(graph, node, T.sourceColumn)
            assert column not in discrepancies
            assert value(graph, node, T.csvPath) == "data/data-constraints.csv"
            assert value(graph, node, T.trackingPath) == "data/spreadsheet-rule-category-tracking.ttl"
            assert value(graph, node, T.authoritativeSource) == "data/data-constraints.csv"
            value(graph, node, T.reason)
            discrepancies[column] = node
        expected_columns = (
            {"Rule Logic"} if rule == "UAD1455" else
            {"Rule Logic", " xPath"} if rule == "UAD1693" else set()
        )
        assert set(discrepancies) == expected_columns
        for column, predicate in FIELDS.items():
            csv_value = value(graph, case, predicate, allow_blank=True)
            local_name = str(predicate).removeprefix(str(T))
            ttl_value = value(tracking, links[0], WT[local_name], allow_blank=True)
            if column in discrepancies:
                node = discrepancies[column]
                assert value(graph, node, T.csvValue, allow_blank=True) == csv_value
                assert value(graph, node, T.trackingValue, allow_blank=True) == ttl_value
                approved = (
                    csv_value.replace("Basement Access", "Below Grade Exterior Access")
                    if rule == "UAD1455" else csv_value.replace("\n", "\r\n")
                )
                assert ttl_value == approved and ttl_value != csv_value
            else:
                assert ttl_value == csv_value
        pair = list(graph.objects(case, T.hasFixture))
        assert len(pair) == 2
        states = {value(graph, node, T.state) for node in pair}
        changed_state = "changed-control" if (rule, value(graph, case, T.caseId)) in CONTROLS else "prohibited"
        assert states == {"permitted", changed_state}
        fixtures.extend(pair)
    assert len(fixtures) == len(set(fixtures)) == 72
    assert set(graph.subjects(RDF.type, T.XMLFixture)) == set(fixtures)
    paths = [value(graph, node, T.path) for node in fixtures]
    assert len(paths) == len(set(paths)) == 72
    saved = {path.relative_to(ROOT).as_posix() for path in (ROOT / FIXTURES).rglob("*.xml")}
    assert saved == set(paths), "Saved XML membership differs from manifest"
    return graph, cases


INVENTORY, CASES = load_inventory()


def binding(node, name, allow_blank=False):
    return value(INVENTORY, node, T[name], allow_blank)


@pytest.fixture(scope="module")
def source_rows():
    with (ROOT / "data/data-constraints.csv").open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        rows, columns = list(reader), reader.fieldnames
    selected = {}
    for rule, unique_id in SOURCE_IDS.items():
        matches = [row for row in rows if row["Message ID"] == rule]
        assert len(matches) == 1 and matches[0]["Unique ID"] == unique_id
        selected[rule] = matches[0]
    return columns, selected


@pytest.fixture(scope="module")
def schema():
    sources = list(INVENTORY.objects(SUITE, T.schemaSource))
    assert sources
    for node in sources:
        path = checked_path(binding(node, "path"))
        assert hashlib.sha256(path.read_bytes()).hexdigest() == binding(node, "sha256")
    path = checked_path(binding(SUITE, "schemaPath"))
    assert hashlib.sha256(path.read_bytes()).hexdigest() == binding(SUITE, "schemaSha256")
    published = checked_path(binding(SUITE, "publishedSourcePath"))
    assert hashlib.sha256(published.read_bytes()).hexdigest() == binding(SUITE, "publishedSourceSha256")
    return etree.XMLSchema(etree.parse(str(path), etree.XMLParser(resolve_entities=False, no_network=True)))


def select(node, path):
    return node.xpath(path, namespaces=NS)


def one(node, path):
    matches = select(node, path)
    assert len(matches) == 1, f"Expected one node for {path}: {len(matches)}"
    return matches[0]


def scalar(node, name):
    values = select(node, "m:" + name)
    assert len(values) == 1, f"Expected one {name}"
    return (values[0].text or "").strip()


def inconsistent_contexts(root, rule):
    """Independent saved-XML oracle; never calls production or generator code."""
    result = []
    for analysis in select(root, "//m:VALUATION_ANALYSIS"):
        properties = one(analysis, "m:PROPERTIES")
        if rule in {"UAD1250", "UAD1455"}:
            role = "GrossRentMultiplierComparable" if rule == "UAD1250" else "SalesComparable"
            types = {GRM_TYPE} if rule == "UAD1250" else SALES_TYPES
            participants = select(properties,
                "m:PROPERTY[@ValuationUseType='SubjectProperty' or "
                f"@ValuationUseType='{role}']")
            assert len(participants) >= 2
            inventories = []
            for prop in participants:
                keys = set()
                for item in select(prop, "m:COMPARABLE/m:COMPARABLE_ADJUSTMENTS/m:COMPARABLE_ADJUSTMENT"):
                    kind = scalar(item, "ComparableAdjustmentType")
                    if kind in types:
                        keys.add((kind, scalar(item, "AdditionalComparisonLineItemIdentifier")))
                inventories.append(keys)
            all_keys = set().union(*inventories)
            if any(keys != all_keys for keys in inventories):
                result.append(properties)
            continue
        if rule == "UAD1461":
            for prop in select(properties, "m:PROPERTY[@ValuationUseType='SalesComparable']"):
                detail = one(prop, "m:COMPARABLE/m:COMPARABLE_DETAIL")
                target = one(detail, "m:SalePriceNetTotalAdjustmentAmount")
                adjustments = select(prop, "m:COMPARABLE/m:COMPARABLE_ADJUSTMENTS/m:COMPARABLE_ADJUSTMENT/m:ComparableAdjustmentAmount")
                total = Decimal("0")
                for amount in adjustments:
                    total += Decimal(amount.text.strip())
                if Decimal(target.text.strip()) != total:
                    result.append(target)
            continue
        for prop in select(properties, "m:PROPERTY[@ValuationUseType='SubjectProperty']"):
            detail = one(prop, "m:PROPERTY_DETAIL")
            improvements = select(prop, "m:IMPROVEMENTS/m:IMPROVEMENT")
            if rule == "UAD1086":
                for improvement in improvements:
                    target = one(improvement, "m:STRUCTURE/m:STRUCTURE_DETAIL/m:LivingUnitCount")
                    if int(target.text) != len(select(improvement, "m:PROPERTY_UNITS/m:PROPERTY_UNIT")):
                        result.append(target)
                continue
            if rule == "UAD1693":
                reported = int(scalar(detail, "AccessoryDwellingUnitTotalCount")) + int(scalar(detail, "LivingUnitExcludingADUCount"))
                counted = sum(int(node.text) for node in select(prop, "m:IMPROVEMENTS/m:IMPROVEMENT/m:STRUCTURE/m:STRUCTURE_DETAIL/m:LivingUnitCount"))
                target = one(detail, "m:LivingUnitExcludingADUCount")
            elif rule == "UAD1016":
                target = one(detail, "m:DwellingCount")
                reported = int(target.text)
                counted = len(select(prop, "m:IMPROVEMENTS/m:IMPROVEMENT/m:IMPROVEMENT_DETAIL[m:ImprovementType='Dwelling']"))
            else:
                name = "AccessoryDwellingUnitTotalCount" if rule == "UAD1011" else "LivingUnitExcludingADUCount"
                target = one(detail, "m:" + name)
                reported = int(target.text)
                indicators = select(prop, "m:IMPROVEMENTS/m:IMPROVEMENT/m:PROPERTY_UNITS/m:PROPERTY_UNIT/m:PROPERTY_UNIT_DETAIL/m:AccessoryDwellingUnitIndicator")
                accepted = {"true", "1"} if rule == "UAD1011" else {"false", "0"}
                counted = len([node for node in indicators if node.text.strip() in accepted])
            if reported != counted:
                result.append(target)
    return result


@pytest.mark.parametrize("case", CASES, ids=lambda case: str(case).removeprefix(str(SUITE) + ":"))
def test_it_1_r13_s1_aggregate_cross_record_consistency(
    case, source_rows, schema, tmp_path, monkeypatch,
):
    columns, rows = source_rows
    rule_id, case_id = binding(case, "ruleId"), binding(case, "caseId")
    row = rows[rule_id]
    for column, predicate in FIELDS.items():
        assert value(INVENTORY, case, predicate, allow_blank=True) == row[column]
    assert fingerprint(row) == binding(case, "sourceFingerprint")
    fixtures = sorted(INVENTORY.objects(case, T.hasFixture), key=lambda node: binding(node, "state") != "permitted")
    parsed, files = [], []
    control = (rule_id, case_id) in CONTROLS
    for fixture in fixtures:
        path = checked_path(binding(fixture, "path"), fixture=True)
        original = path.read_bytes()
        assert hashlib.sha256(original).hexdigest() == binding(fixture, "sha256")
        root = etree.fromstring(original, etree.XMLParser(resolve_entities=False, no_network=True, remove_blank_text=True))
        schema.assertValid(root)
        assert binding(fixture, "xsdValid") is True
        assert binding(fixture, "expectedViolationKind") == "AggregateOrCrossRecordInconsistency"
        expected = 0 if binding(fixture, "state") == "permitted" or control else 1
        assert binding(fixture, "expectedFindingCount") == expected
        bad = inconsistent_contexts(root, rule_id)
        assert len(bad) == expected, "Fixture relationship differs from declared intent"
        if expected:
            assert bad[0] == one(root, binding(case, "targetXPath"))
        parsed.append(root)
        files.append((fixture, path, original))

    replay = deepcopy(parsed[0])
    mutation = one(replay, binding(case, "mutationXPath"))
    kind = binding(case, "mutationKind")
    if kind == "text":
        assert mutation.text == binding(case, "beforeValue", allow_blank=True)
        mutation.text = binding(case, "afterValue", allow_blank=True)
    else:
        assert kind == "remove"
        expected_removed = etree.fromstring(binding(case, "beforeValue").encode("utf-8"))
        assert etree.tostring(mutation, method="c14n", exclusive=True, with_comments=False) == etree.tostring(expected_removed, method="c14n", exclusive=True, with_comments=False)
        mutation.getparent().remove(mutation)
    assert etree.tostring(replay, method="c14n") == etree.tostring(parsed[1], method="c14n"), "Pair contains changes beyond the declared mutation"

    selected_csv = tmp_path / "selected-original-rule.csv"
    with selected_csv.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerow(row)
    monkeypatch.setattr(required_data, "RULE_FILE", selected_csv)
    required_data.load_required_rules.cache_clear()
    try:
        for fixture, path, original in files:
            root = ET.fromstring(original)
            before = ET.tostring(root)
            findings = required_data.evaluate_required_data(root, Investor.BOTH)
            assert ET.tostring(root) == before
            assert path.read_bytes() == original
            expected = binding(fixture, "expectedFindingCount")
            assert len(findings) == expected, (
                f"{rule_id}/{case_id}/{binding(fixture, 'state')}: expected {expected} "
                f"aggregate/cross-record findings; received "
                f"{[(item.rule_id, item.violation_kind) for item in findings]}"
            )
            if not expected:
                continue
            finding = findings[0]
            assert finding.rule_id == rule_id
            assert finding.row_id == row["Unique ID"]
            assert finding.primary_data_element == row["Primary Data Element"]
            assert finding.property_affected == row["Property Affected"]
            assert finding.severity == Severity(row["Severity"].casefold())
            assert finding.investor == Investor.BOTH
            assert finding.rule_type == RuleType.APPENDIX_H
            assert finding.violation_kind == "AggregateOrCrossRecordInconsistency"
            assert finding.finding == row["Message Text"]
            assert finding.expected_condition == row["Rule Logic"]
            assert finding.source is not None
            assert finding.source.source_document == "data/data-constraints.csv"
            assert finding.source.source_version == "UAD 3.6"
            assert finding.source.source_section == row["Unique ID"]
            xml = etree.fromstring(original, etree.XMLParser(resolve_entities=False, no_network=True))
            expected_context = one(xml, binding(case, "targetXPath"))
            assert select(xml, finding.data_location) == [expected_context]
    finally:
        required_data.load_required_rules.cache_clear()