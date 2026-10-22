"""IT-1R2S1: three behavior checks for each governed equality-rule record.

The RDF inventory defines case membership, XML bindings, and expectations.
The configured published workbook supplies governed source values.

The workbook is read once per module. Each evaluator call receives only
the selected workbook row through a temporary replacement of its rule
loader. No CSV derivative or selected-rule file is created.
"""

import re
from pathlib import Path, PurePosixPath
from xml.etree import ElementTree as ET

import app
import pytest
from lxml import etree
from rdflib import Graph, Literal, Namespace, RDF, URIRef

from app.models.enums import Investor, RuleType, Severity
from app.services import required_data
from app.services.gse_constraint_sources import (
    read_active_compliance_workbook_rows,
)


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
VARIANTS = (
    "nonmatching-missing",
    "matching-missing",
    "matching-supplied",
)
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
    "triggerXPath",
    "dependentXPath",
    "nonmatchingValue",
    "expectedDataLocation",
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
    source = read_active_compliance_workbook_rows(
        configuration_path=ROOT / "config" / "configuration.ttl",
    )
    return tuple(
        {
            **row,
            "_source_document": str(source.workbook_path),
            "_source_sheet": source.worksheet_name,
        }
        for row in source.rows
    )


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
    case, variant, source_rows, schema, monkeypatch
):
    rule_id = text(INVENTORY, case, T.ruleId)
    missing = [
        name
        for name in BINDINGS
        if not list(INVENTORY.objects(case, T[name]))
    ]
    if missing:
        pytest.fail(
            f"NOT EXECUTABLE: {rule_id}: missing reviewed RDF bindings: "
            + ", ".join(missing)
            + ". The validator has not been called; this is not behavior RED.",
            pytrace=False,
        )

    binding = {
        name: text(INVENTORY, case, T[name])
        for name in BINDINGS
    }
    matches = [
        row for row in source_rows
        if row["Message ID"] == rule_id
    ]
    assert len(matches) == 1, f"Source rule not unique: {rule_id}"
    rule = matches[0]

    for column, predicate in FIELDS.items():
        actual = text(INVENTORY, case, predicate, allow_blank=True)
        assert actual == rule[column], (
            f"{rule_id}: published workbook and RDF disagree on {column}: "
            f"workbook={rule[column]!r}; RDF={actual!r}. "
            "Review the governed source difference; this is not behavior RED."
        )

    condition = re.fullmatch(
        r'(?i:if)\s+(@?[A-Za-z_][A-Za-z0-9_]*)\s*=\s*"([^"]+)"'
        r'\s*,?\s*and\s+'
        + re.escape(rule["Primary Data Element"])
        + r' is not provided(?: in a given instance of [A-Z_0-9]+)?\s*',
        rule["Rule Logic"],
    )
    assert condition is not None, (
        f"{rule_id}: rule wording needs explicit review"
    )
    trigger_name, matching = condition.groups()
    assert binding["nonmatchingValue"].strip() != matching

    path = fixture_path(binding["baselinePath"])
    original = path.read_bytes()
    parser = etree.XMLParser(resolve_entities=False, no_network=True)
    root = etree.fromstring(original, parser)
    schema.assertValid(root)

    trigger = select_one(root, binding["triggerXPath"])
    dependent = select_one(root, binding["dependentXPath"])
    assert isinstance(dependent, etree._Element) and len(dependent) == 0
    assert dependent.tag == (
        "{" + NS["m"] + "}" + rule["Primary Data Element"]
    )
    assert (
        dependent.get(NIL) not in {"true", "1"}
        and (dependent.text or "").strip()
    )
    assert trigger is not dependent, "Trigger and dependent must be distinct"

    if trigger_name.startswith("@"):
        assert (
            isinstance(trigger, etree._ElementUnicodeResult)
            and trigger.is_attribute
        )
        assert trigger.attrname == trigger_name[1:]
    else:
        assert isinstance(trigger, etree._Element)
        assert trigger.tag == "{" + NS["m"] + "}" + trigger_name
    assert trigger_value(trigger) == matching, "Baseline trigger must match"

    if variant == "nonmatching-missing":
        set_trigger(trigger, binding["nonmatchingValue"])
    if variant != "matching-supplied":
        dependent.getparent().remove(dependent)
    schema.assertValid(root)

    xml = ET.fromstring(etree.tostring(root))
    before = ET.tostring(xml)

    def selected_rules(configuration_path=None):
        return (dict(rule),)

    # Isolate this evaluator behavior test at the rule-loader boundary.
    # The production workbook loader is exercised by the IT-60 tests.
    with monkeypatch.context() as patch:
        patch.setattr(required_data, "load_required_rules", selected_rules)
        findings = required_data.evaluate_required_data(xml, Investor.BOTH)

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
        assert finding.expected_condition
        assert trigger_name in finding.expected_condition
        assert matching in finding.expected_condition
        assert rule["Primary Data Element"] in finding.expected_condition
        assert finding.finding == rule["Message Text"]
        assert finding.source is not None
        assert finding.source.source_section == rule["Unique ID"]