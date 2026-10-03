"""IT-1R11S1: chronological requirements using saved XML and RDF expectations.

Original CSV rows drive production. The test reads the saved corpus without
generating or changing XML files. Current-date comparisons use a fixed clock.
"""

import csv
import datetime
import hashlib
import json
import sys
from pathlib import Path, PurePosixPath
from xml.etree import ElementTree as ET

import app
import pytest
from lxml import etree
from rdflib import Graph, Literal, Namespace, RDF, URIRef

from app.models.enums import Investor, RuleType, Severity
from app.services import required_data


ROOT = Path(app.__file__).resolve().parents[1]
FIXTURES = "tests/fixtures/it_1/r11/s1"
MANIFEST = ROOT / FIXTURES / "manifest.ttl"
T = Namespace("urn:uad36:test-suite:vocab:")
WT = Namespace("urn:uad36:work-tracking:vocab:")
SUITE = URIRef("urn:uad36:test-suite:date-chronology")
SCENARIO = URIRef("urn:uad36:work-tracking:scenario:date_chronology")
NS = {
    "m": "http://www.mismo.org/residential/2009/schemas",
    "xlink": "http://www.w3.org/1999/xlink",
}
REAL_DATE = datetime.date
TODAY = REAL_DATE(2026, 10, 2)
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
EXPECTED_CASES = {
    "UAD1051": {
        "previous-year-boundary", "same-year", "following-year-boundary",
        "not-new-construction-control", "outbuilding-control",
    },
    "UAD1053": {
        "c1-two-year-boundary", "non-c1-effective-year-boundary",
        "outbuilding-control",
    },
    "UAD1131": {"equal-effective-date", "other-property-contract-context"},
    "UAD1206": {"equal-listing-dates", "repeated-listing-context"},
    "UAD1258": {"today-boundary"},
    "UAD1259": {"367-day-boundary"},
    "UAD1505": {"today-boundary"},
    "UAD1506": {"367-day-boundary"},
    "UAD1529": {
        "appraiser-equal-effective-date", "supervisor-equal-effective-date",
        "other-role-control",
    },
    "UAD1536": {"equal-effective-date"},
    "UAD1557": {"equal-effective-date"},
    "UAD1611": {"equal-effective-month", "same-month-earlier-day"},
    "UAD1756": {"equal-effective-date"},
    "UAD1757": {"367-day-boundary"},
}
CONTROLS = {
    ("UAD1051", "not-new-construction-control"),
    ("UAD1051", "outbuilding-control"),
    ("UAD1053", "outbuilding-control"),
    ("UAD1529", "other-role-control"),
}
FUTURE_RULES = {"UAD1258", "UAD1505"}
AGE_RULES = {"UAD1259", "UAD1506", "UAD1757"}


def value(graph, node, predicate, allow_blank=False):
    values = list(graph.objects(node, predicate))
    assert len(values) == 1, f"{node}: expected exactly one {predicate}"
    assert isinstance(values[0], Literal), f"{node}: {predicate} must be literal"
    result = values[0].toPython()
    if isinstance(result, str):
        assert allow_blank or result.strip(), f"{node}: blank {predicate}"
    return result


def binding(node, name, allow_blank=False):
    return value(INVENTORY, node, T[name], allow_blank)


def checked_path(relative):
    path = PurePosixPath(relative)
    assert not path.is_absolute() and ".." not in path.parts
    assert "\\" not in relative and ":" not in relative
    resolved = (ROOT / path).resolve()
    assert resolved.is_relative_to(ROOT.resolve()) and resolved.is_file()
    return resolved


def load_inventory():
    graph = Graph().parse(MANIFEST, format="turtle")
    tracking = Graph().parse(
        ROOT / "data/spreadsheet-rule-category-tracking.ttl",
        format="turtle",
    )
    cases = sorted(graph.objects(SUITE, T.hasCase), key=str)
    assert value(graph, SUITE, T.scenarioId) == "IT-1R11S1"
    assert value(graph, SUITE, T.expectedCaseCount) == len(cases) == 25
    assert value(graph, SUITE, T.expectedFixtureCount) == 50
    assert value(graph, SUITE, T.sourceRuleCount) == 14
    assert value(graph, SUITE, T.evaluationDate) == TODAY.isoformat()
    assert set(graph.subjects(RDF.type, T.TestCase)) == set(cases)

    expected = {
        (rid, name)
        for rid, names in EXPECTED_CASES.items()
        for name in names
    }
    actual = [
        (
            value(graph, case, T.ruleId),
            value(graph, case, T.caseId),
        )
        for case in cases
    ]
    assert len(actual) == len(set(actual)) and set(actual) == expected

    governed = set(tracking.objects(SCENARIO, WT.coversRule))
    assert len(governed) == 14
    assert {
        value(tracking, row, WT.ruleId) for row in governed
    } == set(EXPECTED_CASES)

    fixtures = []
    for case in cases:
        assert value(graph, case, T.scenarioId) == "IT-1R11S1"
        assert value(graph, case, T.evaluationDate) == TODAY.isoformat()
        links = list(graph.objects(case, T.sourceRule))
        assert len(links) == 1 and links[0] in governed
        assert value(tracking, links[0], WT.ruleId) == value(
            graph, case, T.ruleId,
        )
        for column, predicate in FIELDS.items():
            local_name = str(predicate).removeprefix(str(T))
            assert value(
                graph, case, predicate, allow_blank=True,
            ) == value(
                tracking, links[0], WT[local_name], allow_blank=True,
            ), f"Tracking/manifest source mismatch: {case}: {column}"
        pair = list(graph.objects(case, T.hasFixture))
        assert len(pair) == 2
        fixtures.extend(pair)

    assert len(fixtures) == len(set(fixtures)) == 50
    assert set(graph.subjects(RDF.type, T.XMLFixture)) == set(fixtures)
    paths = [value(graph, fixture, T.path) for fixture in fixtures]
    assert len(paths) == len(set(paths)) == 50
    saved = {
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / FIXTURES).rglob("*.xml")
    }
    assert saved == set(paths), "Saved XML membership differs from manifest"
    return graph, cases


INVENTORY, CASES = load_inventory()


@pytest.fixture(scope="module")
def source_rows():
    with (ROOT / "data/data-constraints.csv").open(
        encoding="utf-8-sig", newline="",
    ) as stream:
        reader = csv.DictReader(stream)
        rows, columns = list(reader), reader.fieldnames
    selected = {}
    for rid in EXPECTED_CASES:
        matches = [row for row in rows if row["Message ID"] == rid]
        assert len(matches) == 1, f"{rid}: expected one original CSV row"
        selected[rid] = matches[0]
    return columns, selected


@pytest.fixture(scope="module")
def schema():
    for node in INVENTORY.objects(SUITE, T.schemaSource):
        path = checked_path(binding(node, "path"))
        assert hashlib.sha256(path.read_bytes()).hexdigest() == binding(
            node, "sha256",
        )
    path = checked_path(binding(SUITE, "schemaPath"))
    assert hashlib.sha256(path.read_bytes()).hexdigest() == binding(
        SUITE, "schemaSha256",
    )
    published = checked_path(binding(SUITE, "publishedSourcePath"))
    assert hashlib.sha256(published.read_bytes()).hexdigest() == binding(
        SUITE, "publishedSourceSha256",
    )
    parser = etree.XMLParser(resolve_entities=False, no_network=True)
    return etree.XMLSchema(etree.parse(str(path), parser))


def one(node, xpath):
    selected = node.xpath(xpath, namespaces=NS)
    assert len(selected) == 1, (
        f"Expected one node for {xpath}: {len(selected)}"
    )
    return selected[0]


def owning(node, name):
    return next(
        item for item in node.iterancestors()
        if item.tag == "{" + NS["m"] + "}" + name
    )


def is_prohibited(case, root):
    """Check the fixture's declared relationship independently of production."""
    rid = binding(case, "ruleId")
    target = one(root, binding(case, "targetXPath"))
    raw = target.text
    reference_path = binding(case, "referenceXPath", allow_blank=True)
    reference = binding(case, "referenceValue")
    if reference_path:
        assert one(root, reference_path).text == reference
    else:
        assert rid in FUTURE_RULES | AGE_RULES
        assert reference == TODAY.isoformat()

    if rid in {"UAD1051", "UAD1053"}:
        improvement = owning(target, "IMPROVEMENT")
        kind = one(
            improvement, "m:IMPROVEMENT_DETAIL/m:ImprovementType",
        ).text
        if kind != "Dwelling":
            return False
        year = int(raw)
        effective_year = REAL_DATE.fromisoformat(reference).year
        if rid == "UAD1051":
            subject = owning(target, "PROPERTY")
            indicator = one(
                subject, "m:PROPERTY_DETAIL/m:NewConstructionIndicator",
            ).text
            return indicator == "true" and abs(year - effective_year) > 1
        rating = one(
            improvement,
            "m:STRUCTURE/m:STRUCTURE_DETAIL/m:ExteriorConditionRatingCode",
        ).text
        return year > effective_year + (2 if rating == "C1" else 0)

    if rid == "UAD1611":
        return tuple(map(int, raw[:7].split("-"))) < (
            tuple(map(int, reference[:7].split("-")))
        )

    if rid == "UAD1529":
        role = owning(target, "ROLE")
        role_type = one(role, "m:ROLE_DETAIL/m:PartyRoleType").text
        if role_type not in {"Appraiser", "AppraiserSupervisor"}:
            return False

    parsed = REAL_DATE.fromisoformat(raw)
    other = REAL_DATE.fromisoformat(reference)
    if rid in AGE_RULES:
        return (other - parsed).days > 367
    if rid in FUTURE_RULES | {"UAD1131", "UAD1206", "UAD1557"}:
        return parsed > other
    return parsed < other


def evaluate_original_row(
    rule, columns, root, tmp_path, monkeypatch, as_of=TODAY,
):
    selected = tmp_path / f"{rule['Message ID']}.csv"
    with selected.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerow(rule)
    xml = ET.fromstring(etree.tostring(root))
    before = ET.tostring(xml)

    class FixedDate(REAL_DATE):
        @classmethod
        def today(cls):
            return cls(as_of.year, as_of.month, as_of.day)

    with monkeypatch.context() as patch:
        # Cover datetime.date.today() and already imported date aliases.
        # No production interface or evaluator behavior is added by this test.
        patch.setattr(datetime, "date", FixedDate)
        for name, module in list(sys.modules.items()):
            if name.startswith("app.services.") and module is not None:
                for attribute, item in list(vars(module).items()):
                    if item is REAL_DATE:
                        patch.setattr(module, attribute, FixedDate)
        assert datetime.date.today().isoformat() == as_of.isoformat()
        patch.setattr(required_data, "RULE_FILE", selected)
        required_data.load_required_rules.cache_clear()
        try:
            findings = required_data.evaluate_required_data(
                xml, Investor.BOTH,
            )
            assert ET.tostring(xml) == before, "Validator changed input XML"
            return findings
        finally:
            required_data.load_required_rules.cache_clear()


def assert_findings(findings, expected, case, rule, root):
    rid = binding(case, "ruleId")
    assert len(findings) == expected, (
        f"IT-1R11S1 / {rid} / {binding(case, 'caseId')}: "
        f"expected {expected} chronology finding(s), received {len(findings)}"
    )
    for finding in findings:
        assert finding.rule_id == rid
        assert finding.row_id == rule["Unique ID"]
        assert finding.primary_data_element == rule["Primary Data Element"]
        assert finding.property_affected == rule["Property Affected"]
        assert finding.severity == Severity(rule["Severity"].casefold())
        assert finding.rule_type == RuleType.APPENDIX_H
        assert finding.investor == Investor.BOTH
        assert finding.violation_kind == "ProhibitedDateRelationship"
        assert finding.finding == rule["Message Text"]
        assert finding.expected_condition
        assert finding.data_location
        assert root.xpath(finding.data_location, namespaces=NS) == [
            one(root, binding(case, "targetXPath"))
        ]
        assert finding.source is not None
        assert finding.source.source_document == "data/data-constraints.csv"
        assert finding.source.source_section == rule["Unique ID"]


@pytest.mark.parametrize(
    "case", CASES,
    ids=lambda node: (
        f"{binding(node, 'ruleId')}-{binding(node, 'caseId')}"
    ),
)
def test_it_1_r11_s1_rejects_prohibited_date_relationship(
    case, source_rows, schema, tmp_path, monkeypatch,
):
    rid = binding(case, "ruleId")
    name = binding(case, "caseId")
    columns, rows = source_rows
    rule = rows[rid]
    for column, predicate in FIELDS.items():
        assert value(
            INVENTORY, case, predicate, allow_blank=True,
        ) == rule[column]
    fingerprint = hashlib.sha256(json.dumps(
        [rule[column] for column in FIELDS],
        ensure_ascii=False, separators=(",", ":"),
    ).encode("utf-8")).hexdigest()
    assert fingerprint == binding(case, "sourceFingerprint")

    expected = 0 if (rid, name) in CONTROLS else 1
    assert binding(case, "expectedApplicable") is bool(expected)
    pair = list(INVENTORY.objects(case, T.hasFixture))
    baseline = next(
        node for node in pair if binding(node, "state") == "permitted"
    )
    changed = next(node for node in pair if node != baseline)
    assert binding(baseline, "expectedFindingCount") == 0
    assert binding(changed, "expectedFindingCount") == expected
    assert binding(changed, "state") == (
        "prohibited" if expected else "changed-control"
    )

    documents, saved = {}, {}
    for fixture in (baseline, changed):
        relative = binding(fixture, "path")
        assert relative.startswith(f"{FIXTURES}/{rid}/")
        path = checked_path(relative)
        original = path.read_bytes()
        saved[path] = original
        assert hashlib.sha256(original).hexdigest() == binding(
            fixture, "sha256",
        )
        assert binding(fixture, "xsdValid") is True
        assert binding(
            fixture, "expectedViolationKind",
        ) == "ProhibitedDateRelationship"
        root = etree.fromstring(original, etree.XMLParser(
            resolve_entities=False, no_network=True,
        ))
        schema.assertValid(root)
        target = one(root, binding(case, "targetXPath"))
        assert not len(target)
        assert etree.QName(target).localname == binding(
            case, "targetElement",
        )
        assert target.text == binding(fixture, "targetValue")
        assert bool(root.xpath(
            binding(case, "applicabilityXPath"), namespaces=NS,
        )) is bool(expected)
        documents[fixture] = root

    permitted = documents[baseline]
    prohibited = documents[changed]
    good_target = one(permitted, binding(case, "targetXPath"))
    changed_target = one(prohibited, binding(case, "targetXPath"))
    assert good_target.text == binding(case, "baselineValue")
    assert changed_target.text == binding(case, "changedValue")
    assert good_target.text != changed_target.text
    assert is_prohibited(case, permitted) is False
    assert is_prohibited(case, prohibited) is bool(expected)

    before = etree.tostring(prohibited)
    changed_target.text = good_target.text
    assert etree.tostring(permitted) == etree.tostring(prohibited), (
        "Pair contains an unrelated XML change"
    )
    changed_target.text = binding(case, "changedValue")
    assert etree.tostring(prohibited) == before

    baseline_findings = evaluate_original_row(
        rule, columns, permitted, tmp_path, monkeypatch,
    )
    assert_findings(baseline_findings, 0, case, rule, permitted)
    findings = evaluate_original_row(
        rule, columns, prohibited, tmp_path, monkeypatch,
    )
    assert all(
        path.read_bytes() == original for path, original in saved.items()
    )
    assert_findings(findings, expected, case, rule, prohibited)

    # Prove that current-date results respond to the controlled clock.
    if rid in FUTURE_RULES:
        later = TODAY + datetime.timedelta(days=1)
        findings = evaluate_original_row(
            rule, columns, prohibited, tmp_path, monkeypatch, as_of=later,
        )
        assert_findings(findings, 0, case, rule, prohibited)
    elif rid in AGE_RULES:
        earlier = TODAY - datetime.timedelta(days=1)
        findings = evaluate_original_row(
            rule, columns, prohibited, tmp_path, monkeypatch, as_of=earlier,
        )
        assert_findings(findings, 0, case, rule, prohibited)
        later = TODAY + datetime.timedelta(days=1)
        findings = evaluate_original_row(
            rule, columns, permitted, tmp_path, monkeypatch, as_of=later,
        )
        assert_findings(findings, 1, case, rule, permitted)