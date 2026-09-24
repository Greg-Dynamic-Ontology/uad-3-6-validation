# IT-1R1 / IT-1R1S1 — Conditional and Scoped Requirements Test Summary

## Status

**Planned — tests and fixtures have not yet been created or
executed.**

This document records the intended test design. Expected
failures are predictions based on code inspection, not
observed RED results.
Update this document with execution evidence as RED and GREEN
work is completed.

## Behavior under test

**Iteration:** IT-1  
**Rule:** IT-1R1 — Other conditional or scoped requirements
follow their governed applicability  
**Scenario:** IT-1R1S1 — Enforce a requirement in its
applicable condition and scope

Authoritative feature:
`features/spreadsheet-rule-category-validation.feature`

The Scenario requires three observable states:

1. With applicability conditions unsatisfied and dependent
data absent, no missing-data finding is reported for the
selected source rule.
2. With those conditions satisfied and dependent data absent,
a missing-data finding is reported for that rule.
3. With those conditions still satisfied and the required
dependent value supplied, no finding is reported for that rule.

Findings must identify the source rule, severity, source-row
identity, and affected XML context.

## Source and initial coverage

The governed inventory is
`data/spreadsheet-rule-category-tracking.ttl`,
category `other_conditional_scoped`.
It contains 228 source rules.

The initial coverage slice uses three source rules:

| Source Rule ID | Behavior                                     | Purpose                                                                                                                     |
|----------------|----------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------|
| UAD1021        | OR applicability                             | Require PropertyEstateType when PropertyInProjectIndicator is false or ProjectLegalStructureType is Condominium.            |
| UAD1024        | AND applicability                            | Require PropertyGroundLeaseAnnualAmount when PropertyEstateType is Leasehold and LandOwnedInCommonIndicator is false.       |
| UAD1054        | Applicability within an improvement instance | Require PropertyStructureBuiltYearEstimatedIndicator in the applicable IMPROVEMENT_DETAIL when ImprovementType is Dwelling. |

These examples establish initial behavior coverage. 
Passing them does not establish completion of all 228
category rules.

Case definitions must preserve the source conditions and use
governed values.
Source ambiguity must be resolved explicitly before encoding
an expected result.

## Planned artifacts

Paths below are proposed locations; only this summary document is being delivered at this stage.

| Artifact             | Proposed location                                          | Responsibility                                                                        |
|----------------------|------------------------------------------------------------|---------------------------------------------------------------------------------------|
| Scenario test runner | `tests/test_it_1_r1_s1_conditional_scoped_requirements.py` | Load saved cases, invoke the validator, and assert expected results.                  |
| XML case files       | `tests/fixtures/it_1/r1/s1/<RuleID>/`                      | Provide standalone inputs organized by source rule and descriptive case name.         |
| Case manifest        | `tests/fixtures/it_1/r1/s1/manifest.json`                  | Record case identity, provenance, purpose, expected results, and fixture suitability. |
| Fixture generator    | `scripts/testing/generate_it_1_r1_s1_fixtures.py`          | Reproduce saved XML files from a documented baseline and explicit case changes.       |

The Python test runner will not construct the test XML
internally. 
Generated XML files will be retained for review and reuse
independently of the generator.

The manifest will record:

- Stable case ID and Scenario ID.
- XML filename and source Rule ID.
- Workbook version, sheet, source row number, and source
Unique ID where present.
- Baseline identity and the deliberate changes defining the
case.
- Applicability state and dependent-data state.
- Expected finding count for the selected rule.
- Expected severity and affected XML context for violations.
- Whether the file is a focused validator fixture or a
complete submission-ready appraisal.

Source row number, source Unique ID, and Message ID must
remain distinguishable.

## Planned cases

### UAD1021 — OR condition

Exercise neither condition true, each condition true
independently, and both conditions true, with dependent data
absent.
Also supply the required value under applicable conditions.

These cases distinguish OR behavior from AND behavior and
prove that neither branch is ignored.

### UAD1024 — AND condition

Exercise neither condition true, each condition true
independently, and both conditions true, with dependent data
absent.
Then supply the required value while both conditions remain
true.

These cases prove that one satisfied condition alone does not
activate the requirement.

### UAD1054 — scoped requirement

Exercise a nonapplicable improvement, an applicable
improvement with dependent data absent, and an applicable
improvement with the required value supplied.

Include multiple improvement instances to prove that a
supplied value in another instance cannot satisfy the
deficient instance.
Verify that the finding identifies the deficient context.

## Test mechanism and fixture quality

Use pytest because this Scenario requires executing the XML
validator and examining returned findings.
The TTL provides source traceability; no new SHACL shapes are
planned for this initial slice.

Fixtures must parse successfully and contain the context
necessary to evaluate their conditions.
Verify each fixture against its declared case before treating
a validator failure as behavioral evidence.

Expected results must be derived from the source rules
independently of the implementation under test.
Isolate the selected rules so unrelated findings cannot
substitute for the expected violation.

Focused fixtures are not automatically suitable for external
endpoints.
Complete appraisal files may require additional schema and
submission checks.
Endpoint readiness must be verified and recorded, not
inferred from XML parsing alone.

Provider-specific response adapters are future work.
The saved XML cases and their expected outcomes should remain
usable independently of a particular provider’s response
format.

## Expected RED

Code inspection found that the current required-data
validator supports unconditional requirements and five
explicitly mapped single-equality conditions.

The initial prediction is that applicable, missing-data cases
for these three source rules will fail because the current
loader does not select their conditional definitions.

Nonapplicable and supplied-data cases may pass merely because
a rule is omitted.
Those passes alone do not demonstrate correct implementation.

A valid RED result must expose missing or incorrect
validation behavior.
Import errors, collection failures, broken fixtures, and
unavailable dependencies do not qualify.

## GREEN criteria

For every case in the initial slice:

- Applicability matches the governed condition.
- Missing dependent data produces the expected finding when
applicable.
- Supplying the required value removes that finding.
- Another XML instance cannot satisfy a scoped requirement.
- Findings preserve source identity and severity and identify
the affected context.
- Validation leaves the input fixture unchanged.

Initial-slice GREEN does not mark the entire category complete.

## Execution evidence

| Evidence                                   | Current status |
|--------------------------------------------|----------------|
| Generated fixtures and manifest reviewed   | Not performed  |
| Fixture integrity checks                   | Not performed  |
| Focused RED execution and failure analysis | Not performed  |
| GREEN implementation                       | Not performed  |
| Focused GREEN execution                    | Not performed  |
| Regression suite execution                 | Not performed  |
| External endpoint execution                | Not performed  |

After execution, record the exact commands, execution
environment, tested revision, case counts, results, and paths
to retained output.
Explain each RED failure and any remaining coverage gaps.

## Completion boundary

This work begins IT-1R1S1 with a portable, source-linked test
corpus and focused behavioral tests.
The remaining category rows require further review and
explicit coverage accounting before IT-1R1 can be declared complete.