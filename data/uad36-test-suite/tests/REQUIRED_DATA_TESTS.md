# Required-data test suite

Run from the repository root with its normal Python environment and development dependencies installed:

```sh
python -m pytest tests/test_required_data_fixtures.py -q
python -m pytest tests/test_required_data_acceptance.py -q
python -m pytest tests/test_required_data_fixtures.py tests/test_required_data_acceptance.py --junitxml=required-data-test-results.xml
```

The fixture suite uses lxml and pytest. The acceptance suite additionally imports the repository application and its dependencies. No external server or GraphDB connection is required by the current service.

## Recorded result

55 passed, 53 failed. The fixture baseline/manifest check and all 53 negative fixture checks passed. The production baseline check also passed. All 53 production negative cases failed because ValidationService returned no findings for the expected rule IDs. These failures are intentional acceptance criteria, not marked xfail or skipped; including this file in the normal test suite makes the build fail until implementation is complete.

The production baseline passing alone is not evidence of rule coverage. It is paired with the negative cases.

## Test responsibilities

- Fixture checks: baseline hash, manifest completeness, independent source-row alignment, subject-property selection, exact single-element byte deletion, schema validity and one missing target among the 53 source-derived presence checks.
- Acceptance checks: call the actual ValidationService with each XML; require its expected rule ID and no other rule ID in this 53-rule subset. Other findings outside this subset are allowed.
- Target finding contract: Fatal severity, workbook row_id, and data_location containing the manifest's namespace-aware XPath. The current model has neither a Fatal severity nor row_id; these are explicit proposed acceptance requirements and will need implementation or a documented adapter once the production contract is agreed. No ERROR/CRITICAL mapping is assumed.

Expected results come from the manifest. Production receives only XML, not fixture expectations or workbook-derived test rules. The independent presence checks verify fixture construction and do not substitute for the production evaluator.

API upload/response smoke tests are not included in this suite. The current business-rule service does not yet detect the required-data omissions.

The accompanying ZIP preserves repository-relative paths. Extract it into the matching repository checkout. It contains tests, all fixtures, instructions and the recorded JUnit report; application code is unchanged.
