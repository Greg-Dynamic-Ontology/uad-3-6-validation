# Current State — UAD 3.6 Validation

Updated: 2026-09-27
Document status: Draft for review

## Objective

Implement and verify appraisal validation requirements from the
governed spreadsheet inventory.

Use feature scenarios to describe expected behavior and RDF records
to identify the requirements, organize implementation work, and
record supporting evidence.

For the first release, implement the necessary acceptance scenarios.
Add broader coverage afterward. First-release rule selection is
not yet recorded as approved in the tracker.

## Working locations

Application repository:
C:\Users\grego\projects\uad-3-6-validation

This task's work folder:
C:\Users\grego\.codex\.chatgpt-projects\g-p-6aa7fb39f08c81919fe0cbd6ecbe55dd

The work-folder tracker is a review artifact. Regenerating it does
not update the repository copy.

## Principal files

- features/spreadsheet-rule-category-validation.feature
  Describes the acceptance behavior for 13 rule categories.

- data/spreadsheet-rule-category-tracking.ttl
  Repository tracker connecting scenarios to individual requirements.

- spreadsheet-rule-category-tracking.ttl
  Work-folder copy, including expanded explanations and the
  implementation-subgroup proposals already present in the saved source.

- specs/FannieMae/appendix-h-1-uad-compliance-rules-urar.xlsx
  Published source workbook. The inventory uses the
  "UAD Compliance Rules v1.5" worksheet.

- data/uad36-test-suite/tests/test_required_data_rdf.py
  Existing RDF-driven test runner discussed in this task.
  The work tracker is not an executable replacement for its test data.

## Source inventory

The supplied v1.5 worksheet contains 728 requirements plus a header.
The earlier inventory contained 731 requirements.

UAD1438, UAD1443, and UAD1625 are absent from the current source sheet.
Their absence is an inventory change, not completed implementation work.

| Category | Current requirements |
|---|---:|
| Unconditional required data | 62 |
| Single-equality conditional required data | 174 |
| Other conditional or scoped required data | 228 |
| Required data within an existing context | 22 |
| Required containers or collections | 98 |
| Alternative or mutually exclusive data | 13 |
| Format, precision, or text length | 22 |
| Numeric bounds | 24 |
| Dates and chronology | 14 |
| Value and cross-field consistency | 17 |
| Aggregate and cross-record consistency | 8 |
| Uniqueness and cardinality | 26 |
| Relationships and reference integrity | 20 |
| Total | 728 |

These are the audit's primary categories, not categories published
by Fannie Mae. Each requirement belongs to one primary category.

The feature retains earlier totals of 229 for other conditional/scoped
requirements and 19 for value/cross-field consistency. The tracker
records those values separately from the current source counts.

## How to interpret identifiers and counts

A Rule ID is the workbook's Message ID. It identifies the particular
requirement being implemented and reported in validation findings.

A Unique ID locates the specification entry for the information being
checked. Several requirements can reference the same entry; one
requirement can reference several entries.

Preserve Unique IDs as strings, including leading zeros. Split source
cells containing several IDs, while retaining the original cell text.

Thirty-two requirements have no source Unique ID. Keep those requirements
in the inventory and identify them by Message ID and worksheet row.

Use sourceRuleCount to count requirements.
Use distinctUniqueIdCount to count the different specification entries
those requirements reference.
Neither number counts executed tests.

## Recorded implementation progress

The tracker currently retains this historical assessment:

| Status | Requirements |
|---|---:|
| Done within agreed scope | 53 |
| Partial | 5 |
| Not implemented in the assessed validation path | 670 |
| Total | 728 |

This assessment is dated 2026-09-23 and references commit:
f71d4611a2e7bf3b8747f692d309f23ac4c6fb75

These counts have not been refreshed by a new implementation audit or
acceptance run during preparation of this document.

The five requirements recorded as partial are:
UAD1022, UAD1128, UAD1129, UAD1130, and UAD1135.

"Done within agreed scope" means the agreed behavior was implemented
and previously checked. It does not establish exhaustive coverage.

## Current planning detail

The work-folder tracker contains a proposed subdivision of the
228 other conditional/scoped requirements into 24 implementation groups.

The classification is marked as proposed, not approved. It groups work
by the condition and XML-context handling needed for implementation.
Group membership does not prove implementation or test coverage.

The tracker also contains a proposed next slice of 30 requirements
whose conditions are local to repeated XML instances.

Its notes identify UAD1021, UAD1024, and UAD1054 as the prior initial
slice. Those notes do not establish their current completion status.

The next-slice proposal excludes UAD1054 from the 31 requirements in
the two repeated-local groups. Exact proposed membership is recorded
under r1class:nextSlice using t:proposedSliceRule.

Fixture counts still need to be determined. Thirty requirements do
not necessarily mean thirty XML files or thirty tests.

## Verification evidence and limits

Previously reported by the user:
- RDF-driven suite: 91 passing tests.
- Acceptance suite: 767 passing tests.

These are historical reports, not freshly reproduced results.
Passing-test totals must not be treated as completed spreadsheet rows.

Verified during work-folder tracker regeneration:
- Turtle syntax parses.
- Existing non-definition RDF statements were preserved.
- Fifty-eight explanatory definitions were restored.

Observed while preparing this document:
- 728 RuleWork records.
- 13 Scenario records.
- 24 ImplementationSubgroup records.
- Historical status counts remain 53 / 5 / 670.

No application acceptance tests were run to prepare this document.

## Next work

1. Review this state document and the proposed 30-requirement slice.
2. Confirm the requirements selected for the next implementation step.
3. Derive applicable XML contexts and fixtures from source artifacts.
4. Add the necessary RDF test cases and runner support.
5. Establish meaningful failing tests before changing production behavior.
6. Implement the selected behavior and run focused and regression checks.
7. Update individual tracker statuses with the resulting evidence.

Do not mark work complete solely because it has been classified,
assigned to a scenario, or included in a proposed slice.

## Working agreements

- The user personally applies repository changes unless explicitly
  authorizing direct edits with "EDIT FILES".
- Provide complete replacement files for manual review and application.
- Preserve source IDs, source text, and provenance.
- Do not infer executable XML contexts from element names alone.
- Keep proposed scope separate from approved scope.
- Keep historical test reports separate from newly verified results.
- Do not commit or push without explicit authorization.