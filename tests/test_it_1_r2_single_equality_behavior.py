"""IT-1R2S1: three behavior checks for each governed equality-rule record.

The inventory remains the source of case membership and rule identity. Each
case also needs these reviewed t: predicates before it can execute:

  baselinePath         repository-relative path to a complete XML fixture
  triggerXPath         absolute XPath selecting one element or attribute
  dependentXPath       absolute XPath selecting one supplied scalar element
  nonmatchingValue     schema-valid value unequal to the governed trigger value
  expectedDataLocation exact location expected in the missing-data finding

Paths use the m namespace defined below. The baseline must have the matching
trigger and supplied dependent value. The runner changes only those two data
points in memory. Missing bindings fail explicitly; they are not behavior RED.
No RDF inventory, XML fixture, or production file is written by this runner.
"""

import csv
import re
from pathlib import Path, PurePosixPath
from xml.etree import ElementTree as ET

import app
import pytest
from lxml import etree
from rdflib import Graph, Literal, Namespace, RDF, URIRef

from app.models.enums import Investor, RuleType, Severity
from app.services import required_data


ROOT = Path(app.__file__).resolve().parents[1]
DATA = ROOT / "data/uad36-test-suite/tests/fixtures/single_equality/test-suite.ttl"
SCHEMA = ROOT / (
    "chatgpt-sources/sources/schemas/UAD/GSE_UAD_3.6.0_v1.3/"
    "Combined/GSE_UAD_3.6.0_v1.3.xsd"
)
T = Namespace("urn:uad36:test-suite:vocab:")
SUITE = URIRef("urn:uad36:test-suite:single-equality")
NS = {"m": "http://www.mismo.org/residential/2009/schemas"}
NIL = "{http://www.w3.org/2001/XMLSchema-instance}nil"
VARIANTS = ("nonmatching-missing", "matching-missing", "matching-supplied")
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
    "baselinePath", "triggerXPath", "dependentXPath",
    "nonmatchingValue", "expectedDataLocation",
)


def text(graph, node, predicate, allow_blank=False):
    values = list(graph.objects(node, predicate))
    assert len(values) == 1, f"{node}: expected one {predicate}"
    value = values[0]
    assert isinstance(value, Literal) and isinstance(value.toPython(), str)
    assert allow_blank or str(value).strip(), f"{node}: blank {predicate}"
    return str(value)


def load_inventory():
    graph = Graph().parse(DATA, format="turtle")
    members = sorted(set(graph.objects(SUITE, T.hasCase)), key=str)
    assert len(members) == 174, "Inventory must contain 174 distinct cases"
    rule_ids = set()
    for node in members:
        assert isinstance(node, URIRef)
        assert (node, RDF.type, T.TestCase) in graph
        rule_id = text(graph, node, T.ruleId)
        assert rule_id not in rule_ids, f"Duplicate source rule: {rule_id}"
        rule_ids.add(rule_id)
    return graph, members


INVENTORY, CASES = load_inventory()


@pytest.fixture(scope="module")
def source_rows():
    with required_data.RULE_FILE.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        columns = reader.fieldnames
        rows = list(reader)
    return columns, rows


@pytest.fixture(scope="module")
def schema():
    parser = etree.XMLParser(resolve_entities=False, no_network=True)
    return etree.XMLSchema(etree.parse(str(SCHEMA), parser))


def fixture_path(relative):
    portable = PurePosixPath(relative)
    assert not portable.is_absolute() and ".." not in portable.parts
    assert "\\" not in relative and ":" not in relative
    path = (ROOT / portable).resolve()
    assert path.is_relative_to(ROOT.resolve()), "Fixture escapes repository"
    assert path.suffix.lower() == ".xml" and path.is_file(), str(path)
    return path


def select_one(root, xpath):
    assert xpath.startswith("/"), "Binding must use an absolute XPath"
    nodes = root.getroottree().xpath(xpath, namespaces=NS)
    assert isinstance(nodes, list) and len(nodes) == 1, (
        f"Binding must select exactly one node: {xpath}"
    )
    return nodes[0]


def trigger_value(node):
    if isinstance(node, etree._Element):
        assert len(node) == 0 and node.get(NIL) not in {"true", "1"}
        return (node.text or "").strip()
    assert isinstance(node, etree._ElementUnicodeResult) and node.is_attribute
    return str(node).strip()


def set_trigger(node, value):
    if isinstance(node, etree._Element):
        node.text = value
    else:
        node.getparent().set(node.attrname, value)


@pytest.mark.parametrize("variant", VARIANTS)
@pytest.mark.parametrize(
    "case", CASES, ids=lambda node: text(INVENTORY, node, T.ruleId)
)
def test_it_1_r2_s1_single_equality_behavior(
    case, variant, source_rows, request, tmp_path, monkeypatch
):
    rule_id = text(INVENTORY, case, T.ruleId)
    missing = [name for name in BINDINGS if not list(INVENTORY.objects(case, T[name]))]
    if missing:
        pytest.fail(
            f"NOT EXECUTABLE: {rule_id}: missing reviewed RDF bindings: "
            + ", ".join(missing)
            + ". The validator has not been called; this is not behavior RED.",
            pytrace=False,
        )
    binding = {name: text(INVENTORY, case, T[name]) for name in BINDINGS}
    columns, rows = source_rows
    matches = [row for row in rows if row["Message ID"] == rule_id]
    assert len(matches) == 1, f"Source rule not unique: {rule_id}"
    rule = matches[0]
    for column, predicate in FIELDS.items():
        assert text(INVENTORY, case, predicate, allow_blank=True) == rule[column], (
            f"{rule_id}: source mismatch for {column}"
        )

    # Recognize the governed equality, without inventing its XML binding.
    condition = re.fullmatch(
        r'If\s+(@?[A-Za-z_][A-Za-z0-9_]*)\s*=\s*"([^"]+)"\s*,?\s*and\s+'
        + re.escape(rule["Primary Data Element"])
        + r' is not provided(?: in a given instance of [A-Z_0-9]+)?\s*',
        rule["Rule Logic"],
    )
    assert condition is not None, f"{rule_id}: rule wording needs explicit review"
    trigger_name, matching = condition.groups()
    assert binding["nonmatchingValue"].strip() != matching

    path = fixture_path(binding["baselinePath"])
    original = path.read_bytes()
    parser = etree.XMLParser(resolve_entities=False, no_network=True)
    root = etree.fromstring(original, parser)
    xsd = request.getfixturevalue("schema")
    xsd.assertValid(root)
    trigger = select_one(root, binding["triggerXPath"])
    dependent = select_one(root, binding["dependentXPath"])
    assert isinstance(dependent, etree._Element) and len(dependent) == 0
    assert dependent.tag == "{" + NS["m"] + "}" + rule["Primary Data Element"]
    assert dependent.get(NIL) not in {"true", "1"} and (dependent.text or "").strip()
    assert trigger is not dependent, "Trigger and dependent must be distinct"
    if trigger_name.startswith("@"):
        assert isinstance(trigger, etree._ElementUnicodeResult) and trigger.is_attribute
        assert trigger.attrname == trigger_name[1:]
    else:
        assert isinstance(trigger, etree._Element)
        assert trigger.tag == "{" + NS["m"] + "}" + trigger_name
    assert trigger_value(trigger) == matching, "Baseline trigger must match"

    if variant == "nonmatching-missing":
        set_trigger(trigger, binding["nonmatchingValue"])
    if variant != "matching-supplied":
        dependent.getparent().remove(dependent)
    xsd.assertValid(root)
    prepared = etree.tostring(root)
    xml = ET.fromstring(prepared)
    before = ET.tostring(xml)
    selected = tmp_path / "selected-rule.csv"
    with selected.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerow(rule)
    monkeypatch.setattr(required_data, "RULE_FILE", selected)
    required_data.load_required_rules.cache_clear()
    try:
        findings = required_data.evaluate_required_data(xml, Investor.BOTH)
    finally:
        required_data.load_required_rules.cache_clear()
    assert ET.tostring(xml) == before, "Validator mutated its XML input"
    assert path.read_bytes() == original, "Saved baseline changed"
    expected = 1 if variant == "matching-missing" else 0
    assert len(findings) == expected, (
        f"IT-1R2S1 / {rule_id} / {variant}: expected {expected} findings; "
        f"received {len(findings)}"
    )
    for finding in findings:
        assert finding.rule_id == rule_id
        assert finding.row_id == rule["Unique ID"]
        assert finding.primary_data_element == rule["Primary Data Element"]
        assert finding.severity == Severity(rule["Severity"].casefold())
        assert finding.rule_type == RuleType.APPENDIX_H
        assert finding.property_affected == rule["Property Affected"]
        assert finding.violation_kind == "MissingRequiredValue"
        assert finding.data_location == binding["expectedDataLocation"]
        # The finding may explain the governed condition in reader-friendly
        # wording. Verbatim CSV wording is not a scenario requirement.
        assert finding.expected_condition
        assert trigger_name in finding.expected_condition
        assert matching in finding.expected_condition
        assert rule["Primary Data Element"] in finding.expected_condition
        assert finding.finding == rule["Message Text"]
        assert finding.source is not None
        assert finding.source.source_section == rule["Unique ID"]
