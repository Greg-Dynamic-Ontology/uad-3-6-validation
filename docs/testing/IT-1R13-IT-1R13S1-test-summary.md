# IT-1R13 / IT-1R13S1 test summary

## Behavior

Rule: Aggregates and related records must satisfy governed consistency
requirements.

Scenario: Detect an aggregate or cross-record inconsistency.

For each selected source row, applicable XML containing consistent records
produces no finding for that row. Changing a participating record or
reported aggregate to violate the requirement produces a finding carrying
the governed identity, severity, message, provenance, and affected context.

## Governed scope

The aggregate_cross_record_consistency scenario in
data/spreadsheet-rule-category-tracking.ttl identifies eight source rules.

Production behavior is governed by the original rows in
data/data-constraints.csv.

| Message ID | Unique ID | Requirement | Severity |
| --- | --- | --- | --- |
| UAD1011 | 0100.0019 | Subject ADU total equals the number of PROPERTY_UNIT_DETAIL instances with AccessoryDwellingUnitIndicator=true. | Fatal |
| UAD1016 | 0100.0021 | Subject dwelling count equals the number of IMPROVEMENT_DETAIL instances with ImprovementType=Dwelling. | Fatal |
| UAD1019 | 0100.0022 | Subject living-unit count excluding ADUs equals the number of PROPERTY_UNIT_DETAIL instances with AccessoryDwellingUnitIndicator=false. | Fatal |
| UAD1086 | 0300.0063 | Each subject IMPROVEMENT's LivingUnitCount equals its number of PROPERTY_UNIT instances. | Fatal |
| UAD1250 | 1200.0032 | Additional comparison rows match across the subject and gross-rent-multiplier comparables, using adjustment type and line-item identifier together. | Warning |
| UAD1455 | 1800.0319 | Additional comparison rows match across the subject and sales comparables, using adjustment type and line-item identifier together. | Warning |
| UAD1461 | 1800.0313 | Each sales comparable's net adjustment total equals the sum of its ComparableAdjustmentAmount values. | Fatal |
| UAD1693 | 0300.0063 | Subject ADU total plus living-unit total excluding ADUs equals the sum of LivingUnitCount across its STRUCTURE_DETAIL instances. | Fatal |

UAD1086 and UAD1693 share a Unique ID but govern different requirements.
Coverage and identity checks retain both Message IDs.

All eight CSV rows contain XPath values. Original values are preserved
exactly, including trailing line endings. Explicit fixture bindings are
derived test metadata and remain separate from source XPath values.

## Source reconciliation findings

Inspection found these differences between the CSV and tracking TTL:

- UAD1455 Rule Logic: the CSV example uses "Basement Access"; the TTL
  example uses "Below Grade Exterior Access".
- UAD1693 Rule Logic and XPath: the CSV contains LF line endings where
  the corresponding TTL literals contain CRLF line endings.

The original CSV rows remain authoritative for production behavior and
executable expectations. The published XML remains the fixture source.

The manifest preserves both differing values and their provenance.
Tests verify tracking membership and source identity separately from
these explicitly documented metadata differences.

The UAD1455 example-label difference does not change its requirement to
match adjustment type and identifier across participating properties.

## Artifacts

Test summary:

docs/testing/IT-1R13-IT-1R13S1-test-summary.md

Fixture generator:

scripts/testing/generate_it_1_r13_s1_fixtures.py

Reusable XML corpus and Turtle manifest:

tests/fixtures/it_1/r13/s1/

Test runner:

tests/test_it_1_r13_s1_aggregate_cross_record_consistency.py

Production evaluator:

app/services/aggregate_cross_record_required_data.py

Production dispatcher:

app/services/required_data.py

Fixtures are organized by Message ID and descriptive case name.
Consistent and changed XML are stored as separate files.

The runner reads the saved corpus. It does not generate XML fixtures
inside the test code.

## Fixture construction and validation

Fixtures are derived from published UAD appraisal XML.

Published source hashes and selected CSV definitions are verified before
applying documented fixture changes.

Each pair starts with a consistent baseline. Controlled changes create
business-rule inconsistencies or applicability controls while preserving
XML schema validity.

Every serialized XML fixture is validated against the combined UAD schema
before corpus files are written.

Repeated records use unique labels and valid relationships.
Schema element ordering and resolvable schemaLocation references are
preserved.

The generator supports:

- Default verification without writing project files.
- An explicit write option.
- Protected replacement of previously generated files.
- Reproducible XML and manifest generation.
- Verification of saved file hashes and schema validity.

The user reviewed and ran the generator.

The completed corpus contains 36 case pairs and 72 schema-valid XML files:
28 pairs exercise prohibited inconsistencies, and eight pairs exercise
applicability controls.

| Message ID | Case pairs |
| --- | --- |
| UAD1011 | 3 |
| UAD1016 | 5 |
| UAD1019 | 3 |
| UAD1086 | 3 |
| UAD1250 | 7 |
| UAD1455 | 8 |
| UAD1461 | 4 |
| UAD1693 | 3 |
| Total | 36 |

## Manifest evidence

manifest.ttl records:

- Iteration, Rule, and Scenario.
- Message ID and original Unique ID.
- Original CSV metadata and tracking membership.
- Explicit CSV/TTL metadata differences, preserving both values.
- Published source path and SHA-256.
- Generated fixture path and SHA-256.
- Participating property, improvement, structure, or adjustment contexts.
- Derived fixture bindings separately from original source XPath.
- Documented baseline preparation and controlled mutation.
- Expected finding count, severity, violation kind, and affected location.
- Schema-validation and generation provenance.

Original source metadata and derived test bindings remain distinguishable.

## Coverage

### Counts and structure totals

For UAD1011, UAD1016, UAD1019, UAD1086, and UAD1693:

- Test matching counts and controlled mismatches.
- Exercise qualifying and nonqualifying records.
- Include zero qualifying records where schema-valid.
- Include repeated improvements or structures where applicable.
- Ensure counts remain within the governed subject property.
- Ensure UAD1086 evaluates each improvement independently.
- Ensure unrelated comparable records cannot satisfy a subject total.
- Ensure a matching overall total cannot conceal an incorrect local count.

### Comparable adjustment sums

For UAD1461:

- Verify exact decimal arithmetic.
- Include positive, negative, and zero adjustments.
- Verify a matching reported total and a controlled mismatch.
- Keep each sum within its owning sales comparable.
- Include other comparables so a global sum cannot satisfy a local total.
- Preserve source severity and the affected comparable's identity.

No unsupported rounding tolerance is introduced.

### Matching additional comparison rows

For UAD1250 and UAD1455:

- Test matching rows across the subject and participating comparables.
- Test a missing matching row in a participating property.
- Test a changed line-item identifier.
- Test adjustment type and identifier as a combined key.
- Cover both governed sales adjustment types.
- Include an extra row in a comparable that is absent from the subject.
- Ensure unrelated property roles do not participate.
- Keep comparisons within the owning valuation analysis.

Matching identifiers alone do not establish consistency.

## Test assertions

For each case:

1. Verify exact governed source membership and original CSV metadata.
2. Verify the reviewed CSV/TTL reconciliation differences.
3. Verify source and generated fixture hashes.
4. Validate both XML files against the combined UAD schema.
5. Independently verify that the baseline satisfies the selected requirement.
6. Independently verify the intended inconsistency or applicability control.
7. Evaluate the selected original CSV row through evaluate_required_data.
8. Assert no finding for the consistent baseline.
9. Assert the expected finding count for the changed case.
10. Verify Message ID, Unique ID, severity, message, and provenance.
11. Verify that the reported location identifies the governed context.
12. Verify that evaluation leaves XML inputs and saved files unchanged.

The violation kind is AggregateOrCrossRecordInconsistency.

An independent test oracle computes the expected count, decimal sum, or
cross-record key comparison. It does not call production aggregation logic.

Each selected CSV row is evaluated independently so unrelated chronology,
presence, or other business-rule findings do not obscure the requirement.

## RED completion criteria

RED requires behavioral failures caused by missing aggregate or
cross-record consistency evaluation.

Invalid XML, collection errors, missing files, source mismatches, and
incorrect fixture construction do not establish RED.

Applicability controls may already pass.

The user confirmed the intended RED result before authorizing GREEN.

## Implementation boundary

During RED, only the summary, fixture generator, saved corpus, manifest,
and test runner were supplied.

Production aggregate behavior was implemented after GREEN authorization.

Production validation does not depend on the test manifest or fixture
paths. The dispatcher loads the governed CSV rows and calls the aggregate
evaluator.

This scenario establishes evaluator-level coverage. Programmatic submission
of the corpus through an XML API remains separate endpoint coverage.

The user applies project changes in PyCharm one complete file at a time.

## Execution evidence

Status: GREEN confirmed by the user for the focused tests and complete
acceptance regression.

Source scope: Eight Message IDs, seven distinct Unique IDs.

### Fixture generation

Default verification:

    python scripts/testing/generate_it_1_r13_s1_fixtures.py

Reported:

    Validated 36 case pairs for 8 source rules.
    No saved corpus yet; plan validated in memory. No files written.

Explicit corpus generation:

    python scripts/testing/generate_it_1_r13_s1_fixtures.py --write

Reported:

    Validated 36 case pairs for 8 source rules.
    Wrote 72 schema-valid XML fixtures and manifest.ttl.

Subsequent verification confirmed that the saved XML bytes and manifest
graph matched the generator.

### Confirmed RED

User-confirmed result:

    28 failed, 8 passed in 4.54s

The 28 prohibited-inconsistency cases failed because the expected
aggregate or cross-record finding was absent. The eight applicability
controls passed.

### Confirmed focused GREEN

After saving the aggregate evaluator and its dispatcher integration,
the user confirmed:

    36 passed

Focused command:

    python -B -m pytest tests/test_it_1_r13_s1_aggregate_cross_record_consistency.py -q --tb=short -p no:cacheprovider

### Acceptance regression: temporary-directory errors

The initial full regression reported:

    1965 passed, 453 errors in 1095.76s (0:18:15)

The error excerpts supplied by the user repeatedly reported
FileNotFoundError for the same pytest temporary directory:

    C:\Users\grego\AppData\Local\Temp\pytest-of-grego\pytest-88

Those excerpts showed temporary-directory setup errors across unrelated
tests. They did not establish aggregate-evaluator assertion failures.
The cause of the missing directory was not established.

A diagnostic rerun used a dedicated temporary directory:

    python -B -m pytest tests/test_it_34_r1_s1_enforce_true_condition.py tests/test_xml_schema_validator.py -q --tb=long --maxfail=1 -p no:cacheprovider --basetemp=".pytest-tmp-it1r13-diagnostic"

User-confirmed diagnostic result:

    9 passed in 1.96s

### Confirmed full acceptance GREEN

The complete acceptance selection was rerun with a dedicated temporary
directory:

    python -B -m pytest tests data/uad36-test-suite/tests/test_required_data_acceptance.py data/uad36-test-suite/tests/test_required_data_rdf.py --run-canonical-artifact -q --tb=short -p no:cacheprovider --basetemp=".pytest-tmp-it1r13-regression"

User-confirmed result:

    2418 passed in 1230.02s (0:20:30)

The successful rerun covered the complete acceptance selection, including
canonical artifact checks. No test assertions were weakened or skipped
to resolve the temporary-directory errors.

The dedicated basetemp directories are disposable pytest output locations.
Pytest clears a specified basetemp directory when starting a run; these
directories must be reserved for test output.

### Completion and commit status

IT-1R13S1 focused behavior and full acceptance regression are GREEN.

Commit and push: Pending user confirmation.

Separate XML API endpoint coverage remains outside this scenario.