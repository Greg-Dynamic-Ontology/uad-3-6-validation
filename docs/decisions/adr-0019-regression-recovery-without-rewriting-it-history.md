# ADR-0019: Recover the Regression Baseline Without Rewriting IT History

## Status

Accepted

## Date

2026-10-16

## Context

After IT-51 was committed and pushed, the full regression run reported:

- 637 failed
- 2,674 passed
- 705 errors
- 419.93 seconds elapsed

The causes of these failures and errors have not yet been established.
Earlier comparison of the published GSE workbooks with `data/data-constraints.csv` found discrepancies, including a malformed UAD1065 row, a split UAD1693 rule-logic value, and `Unique ID` values with leading zeroes missing from the CSV. Those findings may explain some failures, but they have not been shown to explain the full regression result.

IT feature files record completed development history.
Retroactively editing those files to describe later regression corrections would
blur the distinction between the original implementation and subsequent
maintenance.
A change-order process was considered, but is deferred while UAD work remains
focused on producing income.

Regression cleanup still requires an auditable explanation of each correction
and its evidence.

## Decision

Regression cleanup will proceed in discrete, documented passes.

Each pass that changes project code or test assets will have its own decision
record under `docs/decisions/`, beginning with ADR-0019, this file.
Each record will explain what changed, why the change was needed, and how the
result was verified.

Completed IT feature files will not be retroactively edited to document
regression cleanup.
Change-order processing will remain deferred.

Each cleanup pass shall:

1. Group failures by an evidenced shared cause rather than by proximity in the
test output.
2. Identify the supporting evidence before making a correction.
3. Record the files changed and explain the reason for each change.
4. Run focused tests for the affected behavior after the correction.
5. Record the resulting test outcome and remaining known failures.
6. Avoid claiming that a correction resolves failures that have not been rerun
or otherwise verified.

The regression baseline in this ADR is the reported 637 failures, 2,674 passes,
and 705 errors. It is a snapshot for the start of recovery, not a diagnosis.

## Consequences

### Positive

- The original purpose and history of completed IT feature files remain intact.
- Each maintenance pass has a reviewable record linking evidence, code changes,
and verification.
- Corrections can be evaluated independently before a new full regression run.
- The project can defer a more complex change-order workflow while still
maintaining traceability.

### Negative

- The decision records add documentation work to each cleanup pass.
- Failures with a shared cause may span many tests and require careful evidence
before being grouped.
- The initial regression result remains unresolved until individual failure
groups are investigated and corrected.

## Follow-up

The next decision record should document the first completed regression-cleanup
pass: its evidenced cause, files changed, rationale, focused test results, and
any remaining uncertainty.

The decision-record index in `docs/decisions/README.md` should be updated when
ADR-0019 is added to the project.