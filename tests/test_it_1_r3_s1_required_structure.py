"""IT-1R3S1: data-driven required-container and collection behavior.

The RDF inventory owns test membership and reviewed XML bindings.
The configured published workbook supplies governed source values.

Missing bindings fail explicitly as NOT EXECUTABLE. They are inventory
work, not behavior failures. The test mutates XML only in memory.
"""

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
    "data/uad36-test-suite/tests/fixtures/required_structures/"
    "required-structures-test-suite.ttl"
)
TRACKING = ROOT / "data/spreadsheet-rule-category-tracking.ttl"
SCHEMA = ROOT / (
    "chatgpt-sources/sources/schemas/UAD/GSE_UAD_3.6.0_v1.3/"
    "Combined/GSE_UAD_3.6.0_v1.3.xsd"
)
T = Namespace("urn:uad36:test-suite:vocab:")
WT = Namespace("urn:uad36:work-tracking:vocab:")
SUITE = URIRef("urn:uad36:test-suite:required-structures")
SCENARIO = URIRef("urn:uad36:work-tracking:scenario:required_structures")
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
    "requiredStructureXPath",
    "expectedDataLocation",
    "xsdValidAfterRemoval",
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
    assert len(members) == 98, "Inventory must contain 98 distinct cases"
    assert len(set(members)) == 98

    for node in members:
        assert (node, RDF.type, T.TestCase) in graph

    source_rules = set(graph.objects(None, T.sourceRule))
    governed = set(tracking.objects(SCENARIO, WT.coversRule))
    assert source_rules == governed, (
        "RDF suite must cover the governed category"
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
    assert path.is_relative_to(ROOT.resolve()), "Fixture escapes repository"
    assert path.suffix.lower() == ".xml" and path.is_file(), str(path)
    return path


def validate_with_only(rule, xml, monkeypatch):
    def selected_rules(configuration_path=None):
        return (dict(rule),)

    with monkeypatch.context() as patch:
        patch.setattr(required_data, "load_required_rules", selected_rules)
        return required_data.evaluate_required_data(xml, Investor.BOTH)


@pytest.mark.parametrize(
    "case",
    CASES,
    ids=lambda node: value(INVENTORY, node, T.ruleId),
)
def test_it_1_r3_s1_detects_an_absent_required_structure(
    case, source_rows, schema, monkeypatch
):
    rule_id = value(INVENTORY, case, T.ruleId)
    matches = [
        row for row in source_rows
        if row["Message ID"] == rule_id
    ]
    assert len(matches) == 1, f"Source rule not unique: {rule_id}"
    rule = matches[0]

    for column, predicate in FIELDS.items():
        recorded_value = value(
            INVENTORY, case, predicate, allow_blank=True
        )
        assert recorded_value == rule[column], (
            f"{rule_id}: published workbook and RDF disagree "
            f"on {column}. Workbook={rule[column]!r}; "
            f"RDF={recorded_value!r}. "
            "Review the source difference before evaluating behavior."
        )

    missing = [
        name
        for name in BINDINGS
        if not list(INVENTORY.objects(case, T[name]))
    ]
    if missing:
        pytest.fail(
            f"NOT EXECUTABLE: {rule_id}: missing reviewed RDF bindings: "
            + ", ".join(missing)
            + ". The validator has not been called; "
            "this is not behavior RED.",
            pytrace=False,
        )

    binding = {
        name: value(INVENTORY, case, T[name])
        for name in BINDINGS
    }
    assert isinstance(binding["xsdValidAfterRemoval"], bool)

    path = fixture_path(binding["baselinePath"])
    original = path.read_bytes()
    parser = etree.XMLParser(resolve_entities=False, no_network=True)
    baseline_root = etree.fromstring(original, parser)
    schema.assertValid(baseline_root)

    baseline = ET.fromstring(etree.tostring(baseline_root))
    before = ET.tostring(baseline)
    assert validate_with_only(rule, baseline, monkeypatch) == []
    assert ET.tostring(baseline) == before, (
        "Validator mutated its XML input"
    )

    negative_root = etree.fromstring(original, parser)
    structures = negative_root.getroottree().xpath(
        binding["requiredStructureXPath"],
        namespaces=NS,
    )
    assert structures, (
        f"{rule_id}: baseline does not contain the required structure"
    )
    assert all(
        isinstance(node, etree._Element)
        for node in structures
    )
    for structure in structures:
        structure.getparent().remove(structure)

    if binding["xsdValidAfterRemoval"]:
        schema.assertValid(negative_root)

    negative = ET.fromstring(etree.tostring(negative_root))
    negative_before = ET.tostring(negative)
    findings = validate_with_only(rule, negative, monkeypatch)
    assert ET.tostring(negative) == negative_before, (
        "Validator mutated its XML input"
    )

    assert len(findings) == 1
    finding = findings[0]
    assert finding.rule_id == rule_id
    assert finding.row_id == rule["Unique ID"]
    assert finding.primary_data_element == rule["Primary Data Element"]
    assert finding.severity == Severity(rule["Severity"].casefold())
    assert finding.rule_type == RuleType.APPENDIX_H
    assert finding.violation_kind == "MissingRequiredStructure"
    assert finding.data_location == binding["expectedDataLocation"]
    assert finding.finding == rule["Message Text"]
    assert finding.source is not None
    assert finding.source.source_section == rule["Unique ID"]
    assert path.read_bytes() == original, "Saved baseline changed"