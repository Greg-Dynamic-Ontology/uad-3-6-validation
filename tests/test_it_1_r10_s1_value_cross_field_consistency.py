"""IT-1R10S1: CSV-verified behavior for all 17 consistency constraint rows.

RDF supplies fixtures and mutations. Original CSV rows drive production.
Install under tests/ with the accompanying RDF and derived XML fixtures.
"""
import csv
import hashlib
from pathlib import Path, PurePosixPath
from xml.etree import ElementTree as ET

import app
import pytest
from lxml import etree
from rdflib import Graph, Literal, Namespace, RDF, URIRef

from app.models.enums import Investor, RuleType, Severity
from app.services import required_data

ROOT = Path(app.__file__).resolve().parents[1]
# In the repository these roots coincide. Separate roots also support staging.
ARTIFACT_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = "tests/fixtures/it_1/r10/s1"
DATA = ARTIFACT_ROOT / FIXTURES / "test-suite.ttl"
CSV = ROOT / "data/data-constraints.csv"
TRACKING = ROOT / "data/spreadsheet-rule-category-tracking.ttl"
SCHEMA = ROOT / (
    "chatgpt-sources/sources/schemas/UAD/GSE_UAD_3.6.0_v1.3/"
    "Combined/GSE_UAD_3.6.0_v1.3.xsd"
)
T = Namespace("urn:uad36:test-suite:vocab:")
WT = Namespace("urn:uad36:work-tracking:vocab:")
SUITE = URIRef("urn:uad36:test-suite:value-cross-field-consistency")
SCENARIO = URIRef("urn:uad36:work-tracking:scenario:value_cross_field_consistency")
NS = {"m": "http://www.mismo.org/residential/2009/schemas",
      "xlink": "http://www.w3.org/1999/xlink"}
FIELDS = {
    "Message ID": T.ruleId, "Unique ID": T.sourceUniqueIdCell,
    "Primary Data Element": T.primaryDataElement, "Rule Logic": T.ruleLogic,
    "Severity": T.severity, "Property Affected": T.propertyAffected,
    " xPath": T.xpath, "Message Text": T.messageText,
}
# Exact reviewed membership: equal counts cannot detect a substituted row.
EXPECTED_IDS = frozenset({
    "UAD1007", "UAD1015", "UAD1029", "UAD1215", "UAD1261", "UAD1272",
    "UAD1512", "UAD1513", "UAD1514", "UAD1515", "UAD1516", "UAD1517",
    "UAD1518", "UAD1533", "UAD1574", "UAD1605", "UAD1730",
})


def value(graph, node, predicate, allow_blank=False):
    items = list(graph.objects(node, predicate))
    assert len(items) == 1, f"Definition error: {node}: expected one {predicate}"
    assert isinstance(items[0], Literal)
    result = items[0].toPython()
    if isinstance(result, str):
        assert allow_blank or result.strip(), f"Blank definition: {predicate}"
    return result


def load_inventory():
    graph = Graph().parse(DATA, format="turtle")
    tracking = Graph().parse(TRACKING, format="turtle")
    cases = sorted(graph.objects(SUITE, T.hasCase), key=str)
    assert value(graph, SUITE, T.expectedCaseCount) == len(cases) == 17
    assert set(graph.subjects(RDF.type, T.TestCase)) == set(cases)
    ids = [value(graph, case, T.ruleId) for case in cases]
    assert len(ids) == len(set(ids)) and set(ids) == EXPECTED_IDS
    governed = set(tracking.objects(SCENARIO, WT.coversRule))
    assert len(governed) == 17
    assert {value(tracking, row, WT.ruleId) for row in governed} == EXPECTED_IDS
    for case in cases:
        links = list(graph.objects(case, T.sourceRule))
        assert len(links) == 1 and links[0] in governed
        assert value(tracking, links[0], WT.ruleId) == value(graph, case, T.ruleId)
        assert value(graph, case, T.scenarioId) == "IT-1R10S1"
    return graph, cases


INVENTORY, CASES = load_inventory()


def checked_path(root, relative):
    portable = PurePosixPath(relative)
    assert not portable.is_absolute() and ".." not in portable.parts
    assert "\\" not in relative and ":" not in relative
    path = (root / portable).resolve()
    assert path.is_relative_to(root.resolve()) and path.is_file()
    return path


@pytest.fixture(scope="module")
def source_rows():
    with CSV.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        rows, columns = list(reader), reader.fieldnames
    selected = {}
    for rid in EXPECTED_IDS:
        matches = [row for row in rows if row["Message ID"] == rid]
        assert len(matches) == 1, f"CSV error: {rid}: expected one original row"
        selected[rid] = matches[0]
    return columns, selected


@pytest.fixture(scope="module")
def schema():
    parser = etree.XMLParser(resolve_entities=False, no_network=True)
    return etree.XMLSchema(etree.parse(str(SCHEMA), parser))


def evaluate_original_row(rule, columns, root, tmp_path, monkeypatch):
    selected = tmp_path / f"{rule['Message ID']}.csv"
    with selected.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerow(rule)  # Original CSV row, never reconstructed from RDF.
    xml = ET.fromstring(etree.tostring(root))
    before = ET.tostring(xml)
    with monkeypatch.context() as patch:
        patch.setattr(required_data, "RULE_FILE", selected)
        required_data.load_required_rules.cache_clear()
        try:
            findings = required_data.evaluate_required_data(xml, Investor.BOTH)
            assert ET.tostring(xml) == before, "Validator changed XML input"
            return findings
        finally:
            required_data.load_required_rules.cache_clear()


@pytest.mark.parametrize("case", CASES, ids=lambda n: value(INVENTORY, n, T.ruleId))
def test_it_1_r10_s1_rejects_inconsistent_field_values(
    case, source_rows, schema, tmp_path, monkeypatch
):
    rid = value(INVENTORY, case, T.ruleId)
    columns, rows = source_rows
    rule = rows[rid]
    for column, predicate in FIELDS.items():
        assert value(INVENTORY, case, predicate, allow_blank=True) == (rule[column] or ""), (
            f"Source mismatch for {rid}, {column}: review CSV and RDF; not behavioral RED"
        )

    def binding(name):
        return value(INVENTORY, case, T[name])

    relative = binding("baselinePath")
    assert relative.startswith(FIXTURES + "/")
    path = checked_path(ARTIFACT_ROOT, relative)
    source = checked_path(ROOT, binding("publishedSourcePath"))
    original, published = path.read_bytes(), source.read_bytes()
    assert hashlib.sha256(original).hexdigest() == binding("baselineSha256")
    assert hashlib.sha256(published).hexdigest() == binding("publishedSourceSha256")
    parser = etree.XMLParser(resolve_entities=False, no_network=True)
    root = etree.fromstring(original, parser)
    tree = root.getroottree()
    schema.assertValid(root)
    applicability = binding("applicabilityXPath")
    assert tree.xpath(applicability, namespaces=NS) is True, f"{rid}: fixture not applicable"
    targets = tree.xpath(binding("targetXPath"), namespaces=NS)
    assert len(targets) == 1, f"{rid}: mutation must identify exactly one element"
    target = targets[0]
    good, bad = binding("baselineValue"), binding("violatingValue")
    assert target.text == good and good != bad
    assert not len(target), "Mutation must target a scalar value"
    baseline_findings = evaluate_original_row(rule, columns, root, tmp_path, monkeypatch)
    assert baseline_findings == [], f"{rid}: consistent baseline produced {baseline_findings!r}"

    before = etree.tostring(root)
    target.text = bad
    assert tree.xpath(applicability, namespaces=NS) is True, f"{rid}: mutation disabled applicability"
    assert binding("xsdValidAfterMutation") is True
    schema.assertValid(root)
    findings = evaluate_original_row(rule, columns, root, tmp_path, monkeypatch)
    target.text = good
    assert etree.tostring(root) == before, f"{rid}: unrelated XML data changed"
    assert path.read_bytes() == original and source.read_bytes() == published

    assert len(findings) == 1, (
        f"IT-1R10S1 / {rid}: consistent baseline accepted; "
        f"changed {etree.QName(target).localname} from {good!r} to {bad!r}; "
        f"expected 1 consistency finding, received {len(findings)}"
    )
    finding = findings[0]
    assert finding.rule_id == rid
    assert finding.row_id == rule["Unique ID"]
    assert finding.primary_data_element == rule["Primary Data Element"]
    assert finding.property_affected == rule["Property Affected"]
    assert finding.severity == Severity(rule["Severity"].casefold())
    assert finding.rule_type == RuleType.APPENDIX_H
    assert finding.violation_kind == binding("expectedViolationKind")
    assert finding.data_location
    assert tree.xpath(finding.data_location, namespaces=NS) == targets
    assert finding.expected_condition
    assert finding.finding == rule["Message Text"]
    assert finding.source is not None
    assert finding.source.source_section == rule["Unique ID"]
