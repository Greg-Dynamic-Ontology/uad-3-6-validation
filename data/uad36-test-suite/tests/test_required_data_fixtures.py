"""Independent checks of the 53 negative inputs, not production rule execution."""
import csv
import hashlib
import json
from pathlib import Path
from xml.parsers import expat

import pytest
from lxml import etree

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / 'tests/fixtures/required_data'
CASES = list(csv.DictReader((FIXTURES / 'manifest.csv').open(encoding='utf-8-sig')))
RULES = json.loads((FIXTURES / 'selected-workbook-rows.json').read_text())
NS = {'m': 'http://www.mismo.org/residential/2009/schemas'}


def parse(raw):
    return etree.fromstring(raw, etree.XMLParser(resolve_entities=False, no_network=True))


def required_path(rule):
    parts = rule[' xPath'].removeprefix('../').strip('/').split('/')
    parts.append(rule['Primary Data Element'])
    return '//' + '/'.join(
        'm:' + name + ("[@ValuationUseType='SubjectProperty']"
        if name == 'PROPERTY' and rule['Property Affected'] == 'Subject' else '')
        for name in parts
    )


@pytest.fixture(scope='module')
def baseline():
    return (FIXTURES / 'baseline/SF1_Appraisal_v1.4.xml').read_bytes()


@pytest.fixture(scope='module')
def schema():
    return etree.XMLSchema(etree.parse(str(ROOT / 'specs/UAD/GSE_UAD_3.6.0_v1.3/Combined/GSE_UAD_3.6.0_v1.3.xsd')))


def test_baseline_and_manifest(baseline, schema):
    assert len(CASES) == len(RULES) == 53
    assert len({case['rule_id'] for case in CASES}) == 53
    assert {case['filename'] for case in CASES} == {p.name for p in (FIXTURES / 'tests').glob('*.xml')}
    provenance = json.loads((FIXTURES / 'verification.json').read_text())
    assert hashlib.sha256(baseline).hexdigest() == provenance['baseline_sha256']
    tree = parse(baseline)
    assert schema.validate(tree), str(schema.error_log)
    for case in CASES:
        rule = next(r for r in RULES if r['Message ID'] == case['rule_id'])
        assert (case['row_id'], case['primary_data_element']) == (rule['Unique ID'], rule['Primary Data Element'])
        assert rule['Severity'] == 'Fatal'
        assert rule['Rule Logic'] == f"If {rule['Primary Data Element']} is not provided"
        assert case['xml_path_context'] == required_path(rule)
        nodes = tree.xpath(required_path(rule), namespaces=NS)
        assert len(nodes) == 1 and (nodes[0].text or '').strip()


@pytest.mark.parametrize('case', CASES, ids=lambda c: c['row_id'] + '-' + c['rule_id'])
def test_fixture(case, baseline, schema):
    original = parse(baseline)
    target = original.xpath(case['xml_path_context'], namespaces=NS)
    assert len(target) == 1 and len(target[0]) == 0
    # Locate actual XML token boundaries, then require exact byte equality.
    spans, stack = [], []
    parser = expat.ParserCreate(namespace_separator='}')
    def start(name, attrs):
        spans.append([parser.CurrentByteIndex, None])
        stack.append(len(spans) - 1)
    def end(name):
        index = stack.pop()
        pos = parser.CurrentByteIndex
        spans[index][1] = baseline.index(b'>', pos) + 1 if baseline[pos:pos+2] == b'</' else pos
    parser.StartElementHandler, parser.EndElementHandler = start, end
    parser.Parse(baseline, True)
    elements = [e for e in original.iter() if isinstance(e.tag, str)]
    assert len(elements) == len(spans)
    start_byte, end_byte = spans[elements.index(target[0])]
    actual = (FIXTURES / 'tests' / case['filename']).read_bytes()
    assert actual == baseline[:start_byte] + baseline[end_byte:]
    modified = parse(actual)
    assert schema.validate(modified), str(schema.error_log)
    missing = []
    for rule in RULES:
        nodes = modified.xpath(required_path(rule), namespaces=NS)
        if not nodes or not any((node.text or '').strip() for node in nodes):
            missing.append(rule['Message ID'])
    assert missing == [case['rule_id']]
