# Governed Constraint Production and Appraisal Evaluation

## Purpose

This feature group defines two related operations:

1. Produce reusable executable constraints from the governed
`data-constraints.csv` source.
2. Evaluate a submitted appraisal XML report against those constraints and
return an auditable evaluation report.

RDF is the shared knowledge representation between governed constraint data,
schema bindings, applicability, validation behavior, generated SHACL, appraisal
data, and findings.

## Governed source and unit of work

`data-constraints.csv` is the authoritative governed source.
The process reads it directly. Converting it to XLS or XLSX adds no value and is
not part of this workflow.

A source row, selected by its governed Unique ID, is the unit of constraint
production.
Each row is processed independently through the applicable construction stages.
A request can select one row or all rows.

## Solution architecture

The solution uses bounded Python stage workers and explicit orchestration.

An **agent** is a Python software component responsible for one defined
transformation.
It receives contracted input, produces contracted RDF knowledge or a
contracted exception, and preserves governed identity and provenance.
An agent does not independently select or reorder stages, advance past
unverified output, or invent missing governed knowledge.

The **orchestrator** selects the requested row or rows, calls the stage workers
in the governed order, verifies each handoff, records status and exceptions,
and resumes eligible work from its last verified stage.
It coordinates the workers without absorbing their knowledge-transformation
responsibilities.

The baseline architecture does not require an LLM or autonomous planning.
The same worker contracts can be retained if an agentic or LLM-assisted
implementation is considered later.

Each Gherkin scenario is bound to its same-named Python test function.
That test function verifies the behavior of the relevant stage contract.
Production orchestration invokes the Python stage workers; it does not
execute Gherkin scenarios as production code.

## Request 1: produce executable constraints

The production request supports two selections:

- **Process row with ID=x** selects one governed row and produces its reusable
constraint artifacts.
- **Process all rows** applies the same production stages to every eligible row
in `data-constraints.csv`.

For each selected row, the construction stages transform governed source
knowledge into executable constraint artifacts:

| Feature                            | Responsibility                                                                              | Result                                                                |
|------------------------------------|---------------------------------------------------------------------------------------------|-----------------------------------------------------------------------|
| IT-50 Normalize constraint         | Read the selected CSV row and produce the agreed normalized constraint RDF.                 | Normalized, source-traceable constraint knowledge.                    |
| IT-51 Governed RDF exchange        | Give each stage result a stable governed identity and exchange it with provenance.          | RDF handoffs that downstream stages can consume.                      |
| IT-52 Bind logical schema          | Bind the normalized constraint to the governed Logical Schema.                              | Traceable schema-binding knowledge.                                   |
| IT-53 Resolve context              | Determine the governed applicability context.                                               | Resolved context knowledge.                                           |
| IT-54 Classify validation behavior | Represent the required validation behavior using established governed knowledge.            | Classified behavior for implementation.                               |
| IT-55 Bind instance RDF            | Map the constraint to the established Instance RDF projection model.                        | A governed binding to the RDF representation used for appraisal data. |
| IT-56 Generate SHACL               | Generate executable SHACL from verified governed knowledge and the established RDF binding. | Constraint-specific SHACL traceable to its governed constraint.       |

The IT-55 Instance RDF binding describes how a constraint reaches the
established projection model.
It does not require a particular appraisal report during constraint production.

Each row advances only after its upstream result has been verified.
If a worker cannot produce its contracted output, the process records a
traceable exception for that row.
Other eligible rows may continue.
Resolved rows can resume from their last verified stage.

Processing all rows produces or updates reusable RDF and SHACL constraint
artifacts.
It does not require an appraisal XML report.
A row’s production is complete when its required reusable constraint artifacts
are verified.

## Request 2: evaluate an appraisal report

When an appraisal XML report is submitted, the validation process uses the
reusable constraint artifacts produced from the CSV:

1. Load the XML report and perform the applicable UAD structure and schema
checks.
2. Project the report into Instance RDF using the established projection model.
3. Evaluate that Instance RDF against the generated SHACL constraints.
4. Use IT-57 to turn SHACL validation results into governed report findings.
5. Return an evaluation report identifying which constraints passed or failed,
with source-rule identity and traceability.

IT-57 runs after SHACL evaluation because its input is the SHACL validation
report.
An actual report finding is created only from a validation result for the
submitted appraisal.

The existing validation features cover the report path:

| Feature                        | Report-evaluation responsibility                                                 |
|--------------------------------|----------------------------------------------------------------------------------|
| IT-38 Upload UAD XML           | Accept an appraisal XML report for validation.                                   |
| IT-39 RDF projection           | Project the loaded appraisal into Instance RDF and preserve source traceability. |
| IT-42 Validate report package  | Perform the applicable report and constraint validation.                         |
| IT-57 Project report finding   | Convert SHACL validation results into governed findings.                         |
| IT-43 Return auditable results | Return findings and supporting audit details through the API.                    |

## Orchestration and governed results

IT-58 coordinates constraint production for the selected row or batch.
It enforces verified handoffs, records stage results and exceptions, and
supports resuming resolved rows without repeating verified work.
It marks constraint production complete when the required reusable RDF and
SHACL artifacts are verified.

Appraisal evaluation uses those completed artifacts through the
report-validation path.
Its findings and run status are associated with the submitted appraisal and
the governed constraints used.

The Batch Results Graph records production row and stage status, generated
results, exceptions, and provenance.
Evaluation results remain traceable to the submitted report, validation results, and governed source constraints.

No worker may invent missing or ambiguous governed knowledge.
The process preserves the exception for review and stops advancement for the
affected row or evaluation stage, while continuing other eligible work where
the contracts allow it.

## RDF's role

RDF connects the CSV source row, normalized constraint, schema binding,
applicability context, validation behavior, Instance RDF binding, generated
SHACL, appraisal data, and report findings.

The submitted appraisal remains XML. Its data is projected to RDF for
evaluation.
The API or user interface can present the resulting governed findings as an
auditable evaluation report.