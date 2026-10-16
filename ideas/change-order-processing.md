# Change Order Processing for UAD 3.6

**Status:** Parked until UAD produces income  
**Purpose:** Preserve the proposed change-order workflow for later review and implementation.

## Why change orders are different

An IT iteration and a change order use opposite decision logic:

- With an **IT**, a failing test shows missing behavior; implementation work makes the test pass.
- With a **CO**, a passing applicability check means the change is appropriate and should be applied. A non-matching check means stop without editing.

A CO is a guarded, one-time change procedure. It is not an ordinary pytest run, and its applicability checks must not be confused with tests of the finished application behavior.

## Required behavior for a CO processor

A future CO processor should:

1. Save a recoverable copy or checkpoint of the current code before changing anything.
2. Evaluate the first applicability check against the actual project state.
3. Apply a change only when that check matches its declared starting state.
4. Stop the whole CO without edits or later steps if a check does not match.
5. After each change, verify the declared resulting state before processing the next step.
6. Make repeated execution a no-op. Once the target state is reached, the original applicability check no longer matches.
7. Report outcomes clearly, such as **APPLIED**, **NOT APPLICABLE**, **ALREADY APPLIED**, or **STOPPED: STATE MISMATCH**.

The processor should not interpret free-form Gherkin as source-code instructions. A CO feature describes the intent and guards; an explicit change plan must identify the authorized edits and their expected results.

## Information each change step must provide

Each step needs:

- A precise, checkable expected starting state.
- The specific files it is authorized to change.
- The exact intended changes.
- The expected resulting state.
- A rule for stopping if the check or result does not match.

Use explicit state checks so an out-of-order CO cannot act on an unexpected project version. Keep each step protected independently so that a later step cannot run in the wrong context.

## Where code and tests belong

Code that changes UAD behavior belongs in the normal production modules that own that behavior. CO-specific orchestration and state checking would live in a separate change-order processor, likely under `scripts/change_orders/`, if that design is adopted.

Application tests validate the resulting UAD behavior after the CO change is applied. They do not execute the CO itself. The processor should not create commits automatically; the existing project commit workflow remains in effect.

## Candidate CO-1

The first candidate change order is to switch constraint production from reading `data-constraints.csv` to resolving the active GSE workbook and rule-data worksheet from `config/configuration.ttl`.

The intended configuration identifies both the Fannie Mae and Freddie Mac workbooks, while `cfg:activeComplianceSource` selects exactly one. The source reader then uses that selected workbook and worksheet to locate a requested governed Unique ID.

IT-50 and IT-51 are complete. A future CO must preserve their accepted behavior and governed RDF contracts rather than rewriting their completed feature files.

The current CO-1 draft is not yet specific enough to execute. Before implementation, it must define its expected starting state, exact file changes, post-change checks, and stop behavior.

## Resume point

Resume this work only after UAD income is established and the user chooses to restart change-order design. Review this document first, then refine CO-1’s guarded change plan before writing or running a processor.