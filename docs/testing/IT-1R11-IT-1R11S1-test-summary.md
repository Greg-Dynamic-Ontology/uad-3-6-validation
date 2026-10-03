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

Create a reproducible fixture generator and a pytest runner.

Store the reusable test corpus under:

tests/fixtures/it_1/r11/s1/

Organize XML files by Rule ID, with descriptive filenames identifying
permitted, boundary, and prohibited cases.

Store fixture definitions and expected results in manifest.ttl.
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

Derive fixtures from available published appraisal XML.

The generator must verify the published source and governed row metadata
before applying explicit, documented changes.

Validate every generated XML file against the combined UAD schema before
writing the corpus. Prohibited chronology must remain schema-valid:
the intended failure is a business-rule violation.

The generator must be reproducible and support a verification mode that
does not replace saved fixtures.

Record both permitted and prohibited cases so the corpus can later support
programmatic endpoint testing.

## Date and boundary coverage

Use a fixed evaluation date of 2026-10-02 for current-date comparisons.
Record it in the manifest and supply it through test-controlled clock
behavior. Do not use the machine's changing date as an expectation.

Cover:

- Equal dates for rules using strict greater-than or less-than comparisons.
- Today versus tomorrow for future-date rules.
- Exactly 367 days old versus 368 days old for age-limit rules.
- C1 and non-C1 branches of UAD1053, including their allowed limits.
- Permitted and prohibited construction years for UAD1051.
- Equal year-month and preceding year-month for UAD1611.
- Appraiser and supervisory-appraiser applicability for UAD1529.
- Nonapplicable conditions and unrelated repeated contexts where relevant.

Compare tax expiration at year-month precision. Compare construction years
at year precision. Compare full dates at date precision.

Choose unambiguous prohibited values. Any unresolved source interpretation
must be identified before an executable expectation is added.

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

Use violation kind ProhibitedDateRelationship for chronology findings.

Evaluate each selected original CSV row independently to prevent unrelated
business-rule findings from obscuring the behavior under test.

This is evaluator-level coverage. HTTP API coverage remains separate.

## Context protection

Date comparisons must use the relevant owning context.

A different property's listing, dwelling, inspection, or tax expiration
cannot satisfy the selected context's requirement.

Report-level comparisons must use the applicable appraisal effective date.
License checks must apply to the specified party roles.
Execution checks must preserve the document/signatory context.

Include controls that reveal accidental comparisons against unrelated
records where applicable.

## RED completion criteria

RED is established only when:

- The test corpus and manifest are valid.
- Every applicable XML fixture passes schema validation.
- Permitted cases produce the expected absence of findings.
- Prohibited cases fail because the governed chronology behavior is missing.

Collection errors, invalid XML, missing files, source mismatches, and clock
setup failures do not establish RED.

Report actual test counts and failure reasons after execution.
Wait for the user's RED confirmation and GREEN authorization.

## Implementation boundary

During RED, supply only the test summary, fixture generator, fixture
definitions, and test runner needed for this scenario.

Production chronology behavior is added during GREEN.

The user applies project changes in PyCharm one complete file at a time.
The user runs the fixture generator after reviewing its write behavior.

## Execution evidence

Status: Test construction beginning.

RED result: Pending.

GREEN result: Pending.

Full acceptance result: Pending.

Commit and push: Pending.