"""IT-1R7S1: governed format, precision, and length behavior."""

import csv
from pathlib import Path, PurePosixPath
from xml.etree import ElementTree as ET

import app
import pytest
from lxml import etree
from rdflib import Graph, Literal, Namespace, RDF, URIRef

from app.models.enums import Investor, RuleType, Severity
from app.services import required_data


ROOT = Path(app.__file__).resolve().parents[1]
DATA = ROOT / (
    "data/uad36-test-suite/tests/fixtures/"
    "representation_restrictions/test-suite.ttl"
)
TRACKING = ROOT / "data/spreadsheet-rule-category-tracking.ttl"
SCHEMA = ROOT / (
    "chatgpt-sources/sources/schemas/UAD/GSE_UAD_3.6.0_v1.3/"
    "Combined/GSE_UAD_3.6.0_v1.3.xsd"
)
T = Namespace("urn:uad36:test-suite:vocab:")
WT = Namespace("urn:uad36:work-tracking:vocab:")
SUITE = URIRef("urn:uad36:test-suite:representation-restrictions")
SCENARIO = URIRef(
    "urn:uad36:work-tracking:scenario:format_precision_length"
)
NS = {"m": "http://www.mismo.org/residential/2009/schemas"}
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
BINDINGS = (
    "baselinePath",
    "mutationMode",
    "mutationXPath",
    "allowedValue",
    "outsideValue",
    "expectedViolationKind",
    "expectedDataLocation",
    "xsdValidAfterMutation",
)


def value(graph, node, predicate, allow_blank=False):
    values = list(graph.objects(node, predicate))
    assert len(values) == 1, f"{node}: expected one {predicate}"
    result = values[0]
    assert isinstance(result, Literal)
    converted = result.toPython()
    if isinstance(converted, str):
        assert allow_blank or converted.strip(), f"{node}: blank {predicate}"
    return converted


def load_inventory():
    graph = Graph().parse(DATA, format="turtle")
    tracking = Graph().parse(TRACKING, format="turtle")
    members = sorted(set(graph.objects(SUITE, T.hasCase)), key=str)
    assert len(members) == 22, "Inventory must contain 22 distinct cases"
    assert all((node, RDF.type, T.TestCase) in graph for node in members)
    assert set(graph.objects(None, T.sourceRule)) == set(
        tracking.objects(SCENARIO, WT.coversRule)
    )
    return graph, members


INVENTORY, CASES = load_inventory()


@pytest.fixture(scope="module")
def source_rows():
    with required_data.RULE_FILE.open(
        encoding="utf-8-sig", newline=""
    ) as stream:
        reader = csv.DictReader(stream)
        return reader.fieldnames, list(reader)


@pytest.fixture(scope="module")
def schema():
    parser = etree.XMLParser(resolve_entities=False, no_network=True)
    return etree.XMLSchema(etree.parse(str(SCHEMA), parser))


def fixture_path(relative):
    portable = PurePosixPath(relative)
    assert not portable.is_absolute() and ".." not in portable.parts
    assert "\\" not in relative and ":" not in relative
    path = (ROOT / portable).resolve()
    assert path.is_relative_to(ROOT.resolve())
    assert path.suffix.lower() == ".xml" and path.is_file()
    return path


def validate_with_only(rule, columns, xml, tmp_path, monkeypatch):
    selected = tmp_path / f"{rule['Message ID']}.csv"
    with selected.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerow(rule)
    monkeypatch.setattr(required_data, "RULE_FILE", selected)
    required_data.load_required_rules.cache_clear()
    try:
        return required_data.evaluate_required_data(xml, Investor.BOTH)
    finally:
        required_data.load_required_rules.cache_clear()


@pytest.mark.parametrize(
    "case", CASES, ids=lambda node: value(INVENTORY, node, T.ruleId)
)
def test_it_1_r7_s1_rejects_value_violating_representation_restriction(
    case, source_rows, schema, tmp_path, monkeypatch
):
    rule_id = value(INVENTORY, case, T.ruleId)
    columns, rows = source_rows
    matches = [row for row in rows if row["Message ID"] == rule_id]
    assert len(matches) == 1
    rule = matches[0]
    for column, predicate in FIELDS.items():
        assert value(
            INVENTORY, case, predicate, allow_blank=True
        ) == rule[column]

    binding = {name: value(INVENTORY, case, T[name]) for name in BINDINGS}
    assert binding["mutationMode"] == "replace-text"
    assert isinstance(binding["xsdValidAfterMutation"], bool)

    path = fixture_path(binding["baselinePath"])
    original = path.read_bytes()
    parser = etree.XMLParser(resolve_entities=False, no_network=True)
    baseline_root = etree.fromstring(original, parser)
    schema.assertValid(baseline_root)
    targets = baseline_root.getroottree().xpath(
        binding["mutationXPath"], namespaces=NS
    )
    assert len(targets) == 1 and isinstance(targets[0], etree._Element)
    assert targets[0].text == binding["allowedValue"]

    baseline = ET.fromstring(etree.tostring(baseline_root))
    before = ET.tostring(baseline)
    assert validate_with_only(
        rule, columns, baseline, tmp_path, monkeypatch
    ) == []
    assert ET.tostring(baseline) == before

    negative_root = etree.fromstring(original, parser)
    negative_targets = negative_root.getroottree().xpath(
        binding["mutationXPath"], namespaces=NS
    )
    assert len(negative_targets) == 1
    negative_targets[0].text = binding["outsideValue"]
    if binding["xsdValidAfterMutation"]:
        schema.assertValid(negative_root)

    negative = ET.fromstring(etree.tostring(negative_root))
    negative_before = ET.tostring(negative)
    findings = validate_with_only(
        rule, columns, negative, tmp_path, monkeypatch
    )
    assert ET.tostring(negative) == negative_before

    assert len(findings) == 1
    finding = findings[0]
    assert finding.rule_id == rule_id
    assert finding.row_id == rule["Unique ID"]
    assert finding.primary_data_element == rule["Primary Data Element"]
    assert finding.severity == Severity(rule["Severity"].casefold())
    assert finding.rule_type == RuleType.APPENDIX_H
    assert finding.violation_kind == binding["expectedViolationKind"]
    assert finding.data_location == binding["expectedDataLocation"]
    assert finding.finding == rule["Message Text"]
    assert finding.source is not None
    assert finding.source.source_section == rule["Unique ID"]
    assert path.read_bytes() == original
