# OTDD Working Conventions

Status: Accepted
Prepared: 2026-09-28
Project: UAD 3.6 Validation

## Purpose

Test-driven development is a disciplined approach to software development
that uses executable tests to define and verify the behavior of the system
under development. The artifacts managed in TDD include requirements,
tests, implementation source code, and evidence of completion.

Ontology Test-Driven Development (OTDD) expands this discipline to include
artifacts generally associated with knowledge representation and validation,
including ontologies, data specifications, XML schemas, mappings, and governed
constraints. Changes to these artifacts can change what the system means,
accepts, rejects, or reports, even when application code is unchanged.

Some software-development artifacts express knowledge about the system:
requirements, meanings, relationships, mappings, or validation decisions.
Their role determines how they are governed, regardless of whether they
are represented in RDF, JSON, YAML, XML, or another format.

In this project, we specifically choose to use RDF to represent 
artifacts that could also have been represented in JSON, YAML, XML,
or another format.

Our design uses a set of tools and techniques that are already needed in the
project to test the RDF artifacts.
Choosing RDF lets this project reuse its existing tools and validation
approach.

In our opinion, the choice of RDF for representing traditional data has
added a certain elegance to the solution by using tools already needed in
the project.
There is no question that data files impact the behavior of the system.
Therefore, to do a complete job of testing system behavior data file change
management is essential.
The choice of RDF is not a requirement for OTDD, but it is a choice that we 
recommend.

In OTDD, each artifact is verified in a manner appropriate to its role.
They are versioned, linked to their sources and
requirements, and accompanied by evidence explaining changes and their
effects.

In traditional development many times data files are outside the change 
control regime used for the source code.
Then a change in a YAML file can slip by unnoticed, until the change causes
unforeseen consequences far away from the knowledge about the change.

OTDD brings all the artifacts together into a change tracking regime that 
is traceable, and testable.

Use OTDD to connect published requirements, expected application behavior,
executable tests, implementation artifacts, and evidence of completion.

Each implementation decision must be traceable to the requirement it
satisfies. Passing tests establish the behavior actually checked;
they do not establish every requirement in the source inventory.

## Source and identity

- Preserve the published requirement text, workbook version,
  worksheet, and source row.
- Use Message ID (Rule ID) to identify the compliance requirement
  within its source version.
- Preserve Unique IDs as strings, including leading zeros.
- A Unique ID locates a data-specification entry. Several requirements
  may reference that entry, and one requirement may reference several
  entries.
- Retain the original Unique ID cell when splitting multiple IDs.
- Keep requirements with blank Unique IDs. Identify them by Message ID
  and source location; do not invent replacement IDs.
- Derive applicability and XML context from source artifacts.
  An element name alone is not enough to select its correct occurrence.
- Record source ambiguities for resolution rather than guessing.
- Preserve published source artifacts. Keep project-owned interpretations,
  mappings, and executable constraints distinguishable from their sources.

## Roles of the artifacts

### Feature files

Describe observable application behavior.

Organize behavior under Rules and Scenarios. Use the established
scenario naming convention for new work. Do not rename existing
tests solely to standardize their names unless requested.

For the first release, keep scenarios to the necessary acceptance
behavior. Add broader coverage deliberately afterward.

### Ontologies, specifications, schemas, and mappings

Describe the meanings, structures, relationships, and correspondences
used by the system.

Identify whether each artifact is a published source or a project-owned
implementation artifact. Preserve published sources and link derived
interpretations to them.

For project-owned artifacts, test the effects relevant to their role.
Examples include whether a mapping selects the intended XML occurrence,
whether a constraint detects a prohibited value, and whether an ontology
change preserves required relationships or query results.

Successful parsing establishes readable syntax. It does not by itself
establish correct meaning or behavior.

### RDF test definitions

Describe the individual cases the runner executes, including the
applicable requirement, fixture or mutation, and expected result.

Keep expected results explicit. The runner must not manufacture an
expected result from the validator's actual output.

### Test runner

Execute the behavior described by the RDF cases and compare the
actual results with their expectations.

Report enough detail to identify the failed case, source requirement,
and relevant XML context.

### Work tracker

Connect scenarios to requirements and record planning and progress.

Category membership, proposed work assignments, and implementation
status are separate facts. Adding a requirement to a scenario does
not implement it or prove that its tests pass.

### Production validator

Evaluate appraisal data against the governed requirements.

Its behavior may be implemented through application code, ontologies,
mappings, schemas, or executable constraints.

Production behavior must not depend on test expectations or test-only
definitions.

## Select a bounded work slice

Before adding behavior:

1. Identify the exact Rule IDs in scope.
2. Inspect their source logic and applicable XML contexts.
3. Identify the implementation behavior they can share.
4. Identify differences that require separate handling.
5. Identify the code and knowledge artifacts that may need to change.
6. Derive the necessary test cases and fixtures.

Keep proposals distinct from approved work.

Do not infer fixture or test counts from the number of requirements.
One requirement may need several cases; one fixture may exercise
several requirements.

## RED: establish the missing behavior

- Add only the tests, fixtures, and feature changes needed for the
  selected behavior.
- Run the smallest relevant test selection.
- Confirm failure because the required behavior is missing or wrong.
  The missing behavior may reside in code, an ontology, a mapping,
  a schema, or an executable constraint.
- A syntax error, missing fixture, failed import, or collection error
  is not a meaningful RED result.
- Do not implement production behavior during this phase, whether
  through code or production knowledge artifacts.
- If testing requires a missing production interface, explain the
  dependency before creating it.
- Present the RED result and wait for authorization to implement.

## GREEN: implement the selected behavior

- Make the smallest production change that satisfies the selected
  requirements. Production changes include changes to project-owned
  code, ontologies, mappings, schemas, and executable constraints.
- Preserve published source artifacts. Correct the project-owned
  interpretation or implementation rather than rewriting its source.
- Do not weaken correct expectations, skip valid cases, or suppress
  failures to obtain a passing result.
- Run the focused tests.
- After focused tests pass, run the established regression suite.
- Report failures and deselections explicitly.
- Do not extend the work into another behavior slice without agreement.

## REFACTOR: improve structure while preserving behavior

After GREEN, improve the structure of code or project-owned knowledge
artifacts when doing so supports the agreed work.

- Preserve required behavior, meaning, source traceability, and external
  interfaces.
- Do not treat a change to a requirement's meaning as refactoring.
  Such a change needs its own scope and acceptance tests.
- Do not weaken tests to accommodate a structural change.
- Rerun affected tests and the established regression checks needed
  to verify that behavior remains unchanged.
- Repository-edit authorization and work-slice boundaries still apply.
  GREEN does not authorize unrelated cleanup.

## XML fixture discipline

- Derive fixtures and contexts from repository or published artifacts.
- Identify the baseline used for each intentional change.
- For a single missing-data case, change only the targeted information
  in the applicable context and preserve unrelated data.
- Preserve namespaces and XML syntax.
- Keep condition inputs associated with the governed occurrence.
  Use data from another property, party, or repeated container only
  when the source requirement explicitly calls for that relationship.
  Preserve the specified association; do not combine unrelated
  occurrences merely because their element names match.
- Distinguish missing, empty, whitespace-only, and nil values when
  the selected behavior requires those cases.
- Do not call a fixture fully valid unless the relevant validation
  scope has actually been checked.

## Evidence and completion

Distinguish:

- Observed results from checks performed in the current session.
- Earlier test results reported by the user.
- Historical assessments retained in the tracker.
- Proposed classifications and implementation plans.

For a test run, record the selection, outcome, and relevant revision
or working-tree state. Include the versions of knowledge artifacts
used when they affect the result. A passing count alone does not
identify what was tested.

Use these tracker statuses consistently:

- Done within agreed scope:
  The agreed behavior is implemented and supported by test evidence.
  This does not claim exhaustive coverage.

- Partial:
  Some behavior works, but identified work remains. Record what remains.

- Not implemented in the current validation path:
  The assessed application flow does not perform the requirement's
  check. Supporting artifacts may still exist.

Update individual work records when evidence changes. Historical
summary counts do not update themselves.

## Counting rules

- Count distinct Rule IDs to measure requirement coverage.
- Count distinct Unique IDs to describe the specification entries
  involved.
- Count executed cases to report test results.
- Keep those counts separate.
- Explain differences between feature-tag totals and source totals.
- Do not count a removed source requirement as completed work.
- Do not equate classification with implementation.

## User-applied repository changes

The user personally applies repository changes unless the current
request includes the exact authorization:

EDIT FILES

Without that authorization:

1. Identify the project-relative destination.
2. Provide the complete replacement file for review.
3. Wait for the user to save it.
4. Inspect or test the saved version when access is available.

Do not provide partial insertion snippets unless requested.

A work-folder draft or download is separate from the repository file.
State which copy was created or changed.

Do not edit read-only synced source material.

## Communication and handoff

- Explain terms by what they mean in practice, how to use them,
  and what conclusions they support.
- State access limitations directly.
- Do not claim that code or knowledge artifacts were saved, inspected,
  tested, or deployed without evidence.
- Keep current-state documents clear about historical results,
  unresolved work, and the next proposed action.
- End change-related responses with a Files changed section.
- Do not commit or push without explicit authorization.