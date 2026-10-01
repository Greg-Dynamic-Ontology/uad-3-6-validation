"""Cross-occurrence and missing-value checks for reviewed equality rules."""
import copy
import csv
from pathlib import Path
from xml.etree import ElementTree as ET

import app
import pytest
from lxml import etree
from rdflib import Graph, Namespace, URIRef

from app.models.enums import Investor
from app.services import required_data

ROOT = Path(app.__file__).resolve().parents[1]
T = Namespace("urn:uad36:test-suite:vocab:")
NS = {"m": "http://www.mismo.org/residential/2009/schemas"}
GRAPH = Graph().parse(ROOT / "data/uad36-test-suite/tests/fixtures/single_equality/test-suite.ttl")
DERIVED = ROOT / "data/uad36-test-suite/tests/fixtures/single_equality/derived"
RULE_IDS = sorted(path.stem for path in DERIVED.glob("*.xml"))


@pytest.fixture(scope="module")
def source():
    with (ROOT / "data/data-constraints.csv").open(encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        return reader.fieldnames, {row["Message ID"]: row for row in reader}


@pytest.fixture(scope="module")
def schema():
    return etree.XMLSchema(etree.parse(str(ROOT / "chatgpt-sources/sources/schemas/UAD/GSE_UAD_3.6.0_v1.3/Combined/GSE_UAD_3.6.0_v1.3.xsd")))


def fixture(rule_id):
    case = URIRef("urn:uad36:test-case:IT-1R2S1:" + rule_id)
    binding = {key: str(GRAPH.value(case, T[key])) for key in ("baselinePath", "dependentXPath", "triggerXPath", "nonmatchingValue")}
    tree = etree.parse(str(ROOT / binding["baselinePath"]), etree.XMLParser(resolve_entities=False, no_network=True))
    return tree, binding


def evaluate(tree, rule_id, source, tmp_path, monkeypatch):
    fields, rows = source
    selected = tmp_path / "selected-rule.csv"
    with selected.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerow(rows[rule_id])
    monkeypatch.setattr(required_data, "RULE_FILE", selected)
    required_data.load_required_rules.cache_clear()
    try:
        return required_data.evaluate_required_data(ET.fromstring(etree.tostring(tree)), Investor.BOTH)
    finally:
        required_data.load_required_rules.cache_clear()


@pytest.mark.parametrize("rule_id", RULE_IDS)
@pytest.mark.parametrize("state", ["empty", "whitespace", "nil"])
def test_matching_condition_rejects_valueless_data(rule_id, state, source, schema, tmp_path, monkeypatch):
    tree, binding = fixture(rule_id)
    dependent = tree.xpath(binding["dependentXPath"], namespaces=NS)[0]
    dependent.text = "   " if state == "whitespace" else None
    if state == "nil":
        dependent.set("{http://www.w3.org/2001/XMLSchema-instance}nil", "true")
    # Empty numeric/date content is deliberately invalid at the schema layer;
    # the required-data layer must still detect its lack of a supplied value.
    if state == "nil":
        schema.assertValid(tree)
    findings = evaluate(tree, rule_id, source, tmp_path, monkeypatch)
    assert len(findings) == 1
    assert findings[0].rule_id == rule_id
    assert findings[0].violation_kind == "MissingRequiredValue"


@pytest.mark.parametrize("rule_id,ancestor", [
    ("UAD1031", "REAL_PROPERTY_INTEREST"),
    ("UAD1082", "IMPROVEMENT"),
    ("UAD1350", "SITE_UTILITY"),
    ("UAD1390", "PROPERTY"),
    ("UAD1486", "PROPERTY"),
    ("UAD1561", "PARTY"),
    ("UAD1770", "SITE_INFLUENCE"),
])
def test_other_occurrence_cannot_supply_trigger(rule_id, ancestor, source, schema, tmp_path, monkeypatch):
    tree, binding = fixture(rule_id)
    dependent = tree.xpath(binding["dependentXPath"], namespaces=NS)[0]
    context = dependent.getparent()
    while etree.QName(context).localname != ancestor:
        context = context.getparent()
    # The added occurrence retains a matching trigger and supplied dependent.
    context.getparent().append(copy.deepcopy(context))
    # Hold direct references: adding a sibling can change absolute indices.
    if binding["triggerXPath"].endswith("/@ValuationUseType"):
        context.set("ValuationUseType", binding["nonmatchingValue"])
    else:
        name = binding["triggerXPath"].split("/")[-1].removeprefix("m:")
        matches = context.xpath(".//m:" + name, namespaces=NS)
        assert len(matches) == 1
        matches[0].text = binding["nonmatchingValue"]
    dependent.getparent().remove(dependent)
    schema.assertValid(tree)
    assert evaluate(tree, rule_id, source, tmp_path, monkeypatch) == []


@pytest.mark.parametrize("rule_id", ["UAD1341", "UAD1582", "UAD1390", "UAD1760"])
def test_missing_dependent_container_is_reported(rule_id, source, schema, tmp_path, monkeypatch):
    tree, binding = fixture(rule_id)
    dependent = tree.xpath(binding["dependentXPath"], namespaces=NS)[0]
    container = dependent.getparent()
    container.getparent().remove(container)
    # An absent optional container must not hide an applicable requirement.
    findings = evaluate(tree, rule_id, source, tmp_path, monkeypatch)
    assert len(findings) == 1
    assert findings[0].rule_id == rule_id
    assert findings[0].nearest_existing_ancestor
