# IT-1R11 / IT-1R11S1 test summary

## Behavior

Rule: Dates must satisfy governed chronological requirements.

Scenario: Reject a prohibited date relationship.

For each selected source row, an applicable appraisal with permitted dates
produces no finding for that row. Changing the relevant date or year to a
prohibited value produces a chronology finding carrying that row's identity,
severity, message, and provenance.

## Governed scope

The date_chronology scenario in
data/spreadsheet-rule-category-tracking.ttl identifies 14 source rows.
The original rows in data/data-constraints.csv govern production behavior.

| Rule ID | Requirement |
| --- | --- |
| UAD1051 | New-construction dwelling year must satisfy the permitted relationship to the appraisal effective year. |
| UAD1053 | Dwelling construction year must satisfy the effective-year limit, including the C1 exception. |
| UAD1131 | Sales contract date must not exceed appraisal effective date. |
| UAD1206 | Listing start date must not exceed listing end date in the same listing. |
| UAD1258 | Appraisal effective date must not be in the future. |
| UAD1259 | Appraisal effective date must not be more than 367 days old. |
| UAD1505 | Execution date must not be in the future. |
| UAD1506 | Execution date must not be more than 367 days old. |
| UAD1529 | Appraiser or supervisory-appraiser license expiration must not precede appraisal effective date. |
| UAD1536 | Execution date must not precede appraisal effective date. |
| UAD1557 | Inspection date must not exceed appraisal effective date. |
| UAD1611 | Tax-abatement or exemption expiration month must not precede the appraisal effective month. |
| UAD1756 | Reconsideration-of-value result date must not precede appraisal effective date. |
| UAD1757 | Reconsideration-of-value result date must not be more than 367 days old. |

The tests verify exact source-rule membership and source metadata.
Matching counts alone cannot establish correct coverage.

## Test files

Fixture generator:

scripts/testing/generate_it_1_r11_s1_fixtures.py

Pytest runner:

tests/test_it_1_r11_s1_date_chronology.py

Reusable test corpus:

tests/fixtures/it_1/r11/s1/

The generated corpus contains 25 case pairs across 14 source rules:
50 schema-valid XML fixtures, comprising 21 prohibited-relationship pairs
and four applicability or context-control pairs.

XML files are organized by Rule ID, with descriptive filenames identifying
permitted, boundary, and prohibited cases.

Fixture definitions and expected results are stored in manifest.ttl.
The manifest records:

- Iteration, Rule, Scenario, and source-rule identity.
- Original CSV metadata and tracking-row reference.
- Published baseline source and its SHA-256.
- Generated XML path and SHA-256.
- Applicable XML context and date fields.
- Evaluation date when the rule depends on the current date.
- Expected finding count, severity, violation kind, and location.
- Schema-validation status and generation provenance.

The test runner reads saved XML files. It does not construct the fixture
corpus inside the Python test file.

## Fixture construction

Fixtures are derived from available published appraisal XML.

The generator verifies the published source and governed row metadata
before applying explicit, documented changes.

Every generated XML file is validated against the combined UAD schema
before the corpus is written. Prohibited chronology remains schema-valid:
the intended failure is a business-rule violation.

The generator is reproducible and supports a verification mode that
does not replace saved fixtures.

Both permitted and prohibited cases are recorded so the corpus can later
support programmatic endpoint testing.

## Date and boundary coverage

The chronology corpus uses a fixed evaluation date of 2026-10-02 for
current-date comparisons. It is recorded in the manifest and supplied
through test-controlled clock behavior. Expectations do not depend on
the machine's changing date.

Coverage includes:

- Equal dates for rules using strict greater-than or less-than comparisons.
- Today versus tomorrow for future-date rules.
- Exactly 367 days old versus 368 days old for age-limit rules.
- C1 and non-C1 branches of UAD1053, including their allowed limits.
- Permitted and prohibited construction years for UAD1051.
- Equal year-month and preceding year-month for UAD1611.
- Appraiser and supervisory-appraiser applicability for UAD1529.
- Nonapplicable conditions and unrelated repeated contexts where relevant.
- Clock changes that move cases across the future-date and age boundaries.

Tax expiration is compared at year-month precision. Construction years
are compared at year precision. Full dates are compared at date precision.

Prohibited values are chosen to express unambiguous governed violations.

## RED assertions

For each case:

1. Verify the original source row against the manifest and tracking inventory.
2. Verify fixture hashes and schema validity.
3. Verify applicability and the intended date relationship.
4. Evaluate the original CSV row through evaluate_required_data.
5. Assert no finding for a permitted case.
6. Assert the expected chronology finding for a prohibited case.
7. Verify Rule ID, Unique ID, severity, source message, and provenance.
8. Verify that the finding location identifies the affected XML context.
9. Verify that evaluation did not alter the XML input or saved files.

Chronology findings use violation kind ProhibitedDateRelationship.

Each selected original CSV row is evaluated independently to prevent
unrelated business-rule findings from obscuring the behavior under test.

This is evaluator-level coverage. HTTP API coverage of the chronology
corpus remains separate.

## Context protection

Date comparisons use the relevant owning context.

A different property's listing, dwelling, inspection, or tax expiration
cannot satisfy the selected context's requirement.

Report-level comparisons use the applicable appraisal effective date.
License checks apply to the specified party roles.
Execution checks preserve the document/signatory context.

Controls reveal accidental comparisons against unrelated records
where applicable.

## RED completion criteria

RED is established only when:

- The test corpus and manifest are valid.
- Every applicable XML fixture passes schema validation.
- Permitted cases produce the expected absence of findings.
- Prohibited cases fail because the governed chronology behavior is missing.

Collection errors, invalid XML, missing files, source mismatches, and clock
setup failures do not establish RED.

The user confirmed RED and authorized GREEN implementation.

## Implementation boundary

During RED, changes were limited to the test summary, fixture generator,
fixture definitions, and test runner needed for this scenario.

During GREEN, production chronology behavior was added in:

app/services/date_chronology_required_data.py

The evaluator was connected through:

app/services/required_data.py

Production behavior is governed by the CSV rows. RDF tracking and fixture
manifests are not production runtime inputs.

The user applied project changes in PyCharm one complete file at a time
and ran the fixture generator after reviewing its write behavior.

## Regression finding and correction

The first full acceptance run after chronology implementation reported
four failures and 2,378 passes.

The failures were:

- tests/test_it_33_r4_s1_actionable_required_data_finding.py:
  test_it_33_r4_s1_actionable_required_data_finding
- tests/test_it_33_r5_s2_positive_and_negative_fixtures.py:
  test_it_33_r5_s2_positive_control
- tests/test_required_data_browser.py:
  test_required_data_upload[chromium-complete-baseline]
- tests/test_required_data_browser.py:
  test_required_data_upload[chromium-missing-subject-address]

These tests use the historical SF1 baseline with appraisal effective and
execution dates of 2019-09-20.

The new evaluator correctly produced UAD1259 and UAD1506 age warnings
when that historical XML was evaluated against the current date.
The baseline therefore produced two findings rather than none.
The missing-address case produced three findings rather than one.

The correction added the explicitly requested
required_data_baseline_clock fixture in tests/conftest.py and connected
the affected tests to it.

Those historical-baseline tests now evaluate as of 2019-09-20.
Production validation continues to use today's date.
The chronology boundary tests retain their separately recorded
evaluation date of 2026-10-02.

No assertions were removed, weakened, or skipped.
The historical XML fixtures were not changed.

## Execution evidence

The following execution results were reported and confirmed by the user.

| Stage | Result | Duration |
| --- | --- | --- |
| Fixture generation | 25 case pairs validated for 14 source rules; 50 schema-valid XML fixtures and manifest.ttl written | Not recorded |
| Initial chronology RED | 21 failed, 4 passed | 4.61 seconds |
| Chronology GREEN | 25 passed | Not recorded |
| Initial full acceptance regression | 4 failed, 2,378 passed | 1,089.48 seconds (18:09) |
| Focused regression after historical-clock correction | 82 passed | 127.90 seconds (2:07) |
| Full acceptance regression after historical-clock correction | 2,382 passed | 1,061.42 seconds (17:41) |

The focused regression command was:

python -B -m pytest tests/test_it_33_r4_s1_actionable_required_data_finding.py tests/test_it_33_r5_s2_positive_and_negative_fixtures.py tests/test_required_data_browser.py tests/test_it_1_r11_s1_date_chronology.py -q --tb=short -p no:cacheprovider

The full acceptance regression was run using:

run-acceptance-test.bat

Status: IT-1R11 / IT-1R11S1 is GREEN, including the full acceptance regression.

Commit and push:

- The chronology implementation was committed and pushed after the user
  confirmed 25 passing chronology tests.
- Commit and push of the historical-clock regression correction and this
  updated summary have not yet been reported.