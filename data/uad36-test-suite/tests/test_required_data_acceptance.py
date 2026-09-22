"""Production acceptance tests. Intentionally red until required rules exist.

No xfail, skips, replacement evaluator or manifest-fed production rule loading.
"""
import csv
from pathlib import Path

import pytest
from app.models.validation import ValidationRequest
from app.services.validation import ValidationService

FIXTURES = Path(__file__).parent / 'fixtures/required_data'
CASES = list(csv.DictReader((FIXTURES / 'manifest.csv').open(encoding='utf-8-sig')))
RULE_IDS = {case['rule_id'] for case in CASES}


def validate(path):
    return ValidationService().validate(ValidationRequest(
        package_name=path.name, xml_text=path.read_text(encoding='utf-8')
    ))


def test_production_baseline_has_no_required_findings():
    result = validate(FIXTURES / 'baseline/SF1_Appraisal_v1.4.xml')
    assert not [f for f in result.findings if f.rule_id in RULE_IDS]


@pytest.mark.parametrize('case', CASES, ids=lambda c: c['row_id'] + '-' + c['rule_id'])
def test_production_detects_missing_required_data(case):
    result = validate(FIXTURES / 'tests' / case['filename'])
    findings = [f for f in result.findings if f.rule_id in RULE_IDS]
    assert {f.rule_id for f in findings} == {case['rule_id']}, (
        f"Expected {case['rule_id']} for missing {case['primary_data_element']}; "
        f"received {[f.rule_id for f in findings]}"
    )
    matching = [f for f in findings if f.rule_id == case['rule_id']]
    # Explicit target contract: do not silently equate Fatal with ERROR/CRITICAL.
    assert any(
        str(f.severity).lower() == 'fatal'
        and getattr(f, 'row_id', None) == case['row_id']
        and f.data_location == case['xml_path_context']
        for f in matching
    ), 'Finding must expose Fatal severity, workbook row_id and the manifest context XPath'
