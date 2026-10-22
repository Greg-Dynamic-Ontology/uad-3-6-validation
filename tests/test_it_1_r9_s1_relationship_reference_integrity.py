"""IT-1R9S1: governed relationship and reference integrity behavior.

RDF supplies test membership, XML fixtures, and mutations.
The configured published workbook supplies governed source values.
Each evaluator call receives only the selected rule.
"""

import copy
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
DATA = ROOT / (
    "data/uad36-test-suite/tests/fixtures/relationship_reference_integrity/"
    "test-suite.ttl"
)
TRACKING = ROOT / "data/spreadsheet-rule-category-tracking.ttl"
SCHEMA = ROOT / (
    "chatgpt-sources/sources/schemas/UAD/GSE_UAD_3.6.0_v1.3/"
    "Combined/GSE_UAD_3.6.0_v1.3.xsd"
)
T = Namespace("urn:uad36:test-suite:vocab:")
WT = Namespace("urn:uad36:work-tracking:vocab:")
SUITE = URIRef("urn:uad36:test-suite:relationship-reference-integrity")
SCENARIO = URIRef(
    "urn:uad36:work-tracking:scenario:relationship_reference_integrity"
)
NS = {
    "m": "http://www.mismo.org/residential/2009/schemas",
    "xlink": "http://www.w3.org/1999/xlink",
}
X = "{http://www.w3.org/1999/xlink}"
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
    "relationshipXPath",
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
        assert allow_blank or converted.strip(), (
            f"{node}: blank {predicate}"
        )
    return converted


def load_inventory():
    graph = Graph().parse(DATA, format="turtle")
    tracking = Graph().parse(TRACKING, format="turtle")
    members = sorted(set(graph.objects(SUITE, T.hasCase)), key=str)

    assert len(members) == 20, "Inventory must contain 20 distinct cases"
    assert all(
        (node, RDF.type, T.TestCase) in graph
        for node in members
    )
    assert set(graph.objects(None, T.sourceRule)) == set(
        tracking.objects(SCENARIO, WT.coversRule)
    )
    return graph, members


INVENTORY, CASES = load_inventory()


@pytest.fixture(scope="module")
def source_rows():
    workbook = read_active_compliance_workbook_rows(
        configuration_path=ROOT / "config" / "configuration.ttl",
    )
    return tuple(
        {
            **row,
            "_source_document": str(workbook.workbook_path),
            "_source_sheet": workbook.worksheet_name,
        }
        for row in workbook.rows
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
    assert path.is_relative_to(ROOT.resolve()), (
        f"Fixture escapes repository: {relative}"
    )
    assert path.suffix.lower() == ".xml" and path.is_file(), (
        f"Missing XML fixture: {path}"
    )
    return path


def validate_with_only(rule, xml, monkeypatch):
    def selected_rules(configuration_path=None):
        return (dict(rule),)

    with monkeypatch.context() as patch:
        patch.setattr(required_data, "load_required_rules", selected_rules)
        return required_data.evaluate_required_data(xml, Investor.BOTH)


def relationship_key(node):
    return (
        node.get(X + "arcrole", ""),
        node.get(X + "from", ""),
        node.get(X + "to", ""),
    )


@pytest.mark.parametrize(
    "case",
    CASES,
    ids=lambda node: value(INVENTORY, node, T.ruleId),
)
def test_it_1_r9_s1_rejects_invalid_relationship_or_reference(
    case, source_rows, schema, monkeypatch
):
    rule_id = value(INVENTORY, case, T.ruleId)
    matches = [
        row for row in source_rows
        if row["Message ID"] == rule_id
    ]
    assert len(matches) == 1, (
        f"The configured workbook must contain exactly one {rule_id}."
    )
    rule = matches[0]

    for column, predicate in FIELDS.items():
        recorded_value = value(
            INVENTORY, case, predicate, allow_blank=True
        )
        source_value = rule[column] or ""
        assert recorded_value == source_value, (
            f"{rule_id}: published workbook and RDF disagree "
            f"on {column}. Workbook={source_value!r}; "
            f"RDF={recorded_value!r}. "
            "Review the source difference before evaluating behavior."
        )

    binding = {
        name: value(INVENTORY, case, T[name])
        for name in BINDINGS
    }
    assert isinstance(binding["xsdValidAfterMutation"], bool)

    path = fixture_path(binding["baselinePath"])
    original = path.read_bytes()
    parser = etree.XMLParser(resolve_entities=False, no_network=True)
    baseline_root = etree.fromstring(original, parser)
    schema.assertValid(baseline_root)

    relationships = baseline_root.getroottree().xpath(
        binding["relationshipXPath"],
        namespaces=NS,
    )
    assert relationships
    labels = set(
        baseline_root.getroottree().xpath(
            "//@xlink:label",
            namespaces=NS,
        )
    )
    assert all(
        node.get(X + "from") in labels
        for node in relationships
    )
    assert all(
        node.get(X + "to") in labels
        for node in relationships
    )

    baseline = ET.fromstring(etree.tostring(baseline_root))
    before = ET.tostring(baseline)
    assert validate_with_only(rule, baseline, monkeypatch) == []
    assert ET.tostring(baseline) == before

    negative_root = etree.fromstring(original, parser)
    targets = negative_root.getroottree().xpath(
        binding["relationshipXPath"],
        namespaces=NS,
    )
    mode = binding["mutationMode"]

    if mode == "remove-relationships":
        for target in targets:
            target.getparent().remove(target)
        assert not negative_root.getroottree().xpath(
            binding["relationshipXPath"],
            namespaces=NS,
        )
    elif mode == "duplicate-relationship":
        assert len(targets) == 1
        targets[0].addnext(copy.deepcopy(targets[0]))
        keys = [
            relationship_key(node)
            for node in negative_root.iter()
            if node.tag.endswith("RELATIONSHIP")
        ]
        assert len(keys) != len(set(keys))
    elif mode == "replace-from":
        assert len(targets) == 1
        targets[0].set(X + "from", "MISSING_RELATIONSHIP_SOURCE")
        assert targets[0].get(X + "from") not in labels
    elif mode == "replace-to":
        assert len(targets) == 1
        targets[0].set(X + "to", "MISSING_RELATIONSHIP_TARGET")
        assert targets[0].get(X + "to") not in labels
    else:
        pytest.fail(f"Unsupported mutation mode: {mode}")

    if binding["xsdValidAfterMutation"]:
        schema.assertValid(negative_root)

    negative = ET.fromstring(etree.tostring(negative_root))
    negative_before = ET.tostring(negative)
    findings = validate_with_only(rule, negative, monkeypatch)
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