# ADR-0009 — Canonical Intermediate Saves

**Status:** Accepted

**Date:** 2026-07-28

## Context

Ontology Test-Driven Development organizes a transformation as a sequence of
milestones.

Each milestone produces a canonical internal representation that becomes the
input to the next milestone.

For example:

```text
Milestone 1
XML Schema
    │
    ▼
Logical Schema Model

Milestone 2
Logical Schema Model
    │
    ▼
Ontology Model
```
The canonical representation may be passed directly from one milestone to the
next as an in-memory object.

It may also be serialized as a persistent RDF artifact:
```text
Logical Schema Model
    │
    ▼
logical-schema.ttl
```
Persistent intermediate artifacts are useful because they make milestone
boundaries:

- visible,
- inspectable,
- reproducible,
- independently testable,
- available for regression testing,
- available as inputs to later milestones,
- suitable for documentation and publication.

Persistent intermediate artifacts also introduce serialization,
deserialization, and file-system overhead.

Normal pipeline execution should therefore be able to pass canonical
representations directly in memory, while development and verification
executions should be able to save and reload those same representations.

The desired behavior must be communicated to the pipeline explicitly and
declaratively.

---

## Decision
Pipeline initialization shall be controlled by an RDF initialization document
named:
```text
init.ttl
```
The initialization document shall describe:

1. whether canonical intermediate representations are saved,
2. whether a milestone receives its input from memory or from a saved
3. intermediate artifact,
4. where saved artifacts are written,
5. where previously saved artifacts are loaded from.

The initialization document is a configuration expressed as RDF.

It is not an intermediate model itself. It describes how the OTDD pipeline is
to execute.

---

## Canonical Representations
Each milestone shall expose one canonical internal representation.

For Milestone 1, the canonical representation is the Logical Schema Model.

That model may exist in two forms:
```text
In-memory form
    LogicalSchemaModel Python object

Persistent form
    logical-schema.ttl RDF graph
```
These are two representations of the same milestone result.

The in-memory representation is used for efficient pipeline execution.

The persistent representation is used for inspection, restart, regression
testing, documentation, and independent milestone execution.

---
## Saving and Loading Are Separate Decisions
Saving an intermediate artifact and loading a milestone from an intermediate
artifact are related but distinct operations.

A pipeline may:
* pass a model in memory without saving it,
* pass a model in memory and also save it,
* load a previously saved model instead of executing the preceding milestone.

---
Therefore, init.ttl shall distinguish between:
```text
save the output
```
and
```text
load the input
```
Saving does not require the next milestone to reload the artifact during the
same execution.

For example:
```text
Milestone 1
    generates Logical Schema Model
    saves logical-schema.ttl
    passes Logical Schema Model directly to Milestone 2

Milestone 2
    receives the in-memory model
```
This preserves the intermediate artifact without paying the cost of
serializing and immediately deserializing it.

---
## Initialization Graph
The initialization document shall contain an RDF graph describing the pipeline
execution.

A minimal namespace declaration may be:
```turtle
@prefix otdd: <https://dynamicontology.com/otdd#> .
```
A pipeline initialization resource may be represented as:
```turtle
@prefix otdd: <https://dynamicontology.com/otdd#> .

<urn:otdd:execution>
    a otdd:PipelineInitialization .
```
The resource identifies the configuration for one pipeline execution.

The exact subject IRI may be project-specific. A stable local IRI or a blank
node may also be used.

For example:
```turtle
@prefix otdd: <https://dynamicontology.com/otdd#> .

[]
    a otdd:PipelineInitialization .
```
A named resource is preferable when initialization graphs are retained as
records of executions.
## Initialization Vocabulary
The initialization graph shall support the following concepts.
### Pipeline initialization

```turtle
otdd:PipelineInitialization
    ```
Identifies a resource that describes how a pipeline execution is initialized.

### Milestone configuration

```turtle
otdd:MilestoneInitialization
```
Identifies the initialization instructions for one milestone.

### Milestone association

```turtle
otdd:hasMilestoneInitialization
```
Associates the pipeline initialization with a milestone initialization.

### Milestone identifier

```turtle
otdd:milestone
```
Identifies the milestone to which the instructions apply.

### Input source
```turtle
otdd:inputSource
```
Specifies where the milestone receives its canonical input.
Identifies the source of the input to the milestone.

Supported values are:
```turtle
otdd:InMemory
otdd:IntermediateArtifact
```
### Save intermediate output
```turtle
otdd:saveIntermediate
```
A Boolean value specifying whether the milestone output shall be serialized.

### Intermediate artifact
```turtle
otdd:intermediateArtifact
```
Specifies the location of the persistent intermediate artifact.

The location may be expressed as a relative project path or as a file IRI,
depending on the execution environment.

---
## Input Sources
### In-memory input
When a milestone uses:
```turtle
otdd:inputSource otdd:InMemory
```
the milestone receives the canonical representation produced by the preceding
milestone during the current pipeline execution.

Example:
```turtle
@prefix otdd: <https://dynamicontology.com/otdd#> .

<urn:otdd:milestone-2-init>
    a otdd:MilestoneInitialization ;
    otdd:milestone <urn:otdd:milestone-2> ;
    otdd:inputSource otdd:InMemory .
```
The resulting execution is:
```text
Milestone 1
    │
    │ Logical Schema Model in memory
    ▼
Milestone 2
```
No intermediate artifact is required for Milestone 2 initialization.

---
### Intermediate artifact input
When a milestone uses:
```turtle
otdd:inputSource otdd:IntermediateArtifact
```
The milestone reconstructs its canonical input from a saved RDF artifact.
Example:
```turtle
@prefix otdd: <https://dynamicontology.com/otdd#> .

<urn:otdd:milestone-2-init>
    a otdd:MilestoneInitialization ;
    otdd:milestone <urn:otdd:milestone-2> ;
    otdd:inputSource otdd:IntermediateArtifact ;
    otdd:intermediateArtifact
        "docs/milestones/milestone-1/artifacts/logical-schema.ttl" .
```
The resulting execution is:
```text
logical-schema.ttl
    │
    ▼
Logical Schema Model
    │
    ▼
Milestone 2
```
Milestone 1 does not need to be executed during that pipeline run.

## Saving Intermediate Output
A milestone saves its canonical output when:
```turtle
otdd:saveIntermediate true
```
Example:
```turtle
@prefix otdd: <https://dynamicontology.com/otdd#> .

<urn:otdd:milestone-1-init>
    a otdd:MilestoneInitialization ;
    otdd:milestone <urn:otdd:milestone-1> ;
    otdd:saveIntermediate true ;
    otdd:intermediateArtifact
        "docs/milestones/milestone-1/artifacts/logical-schema.ttl" .
```
The milestone shall:

1. produce its canonical in-memory representation,
2. serialize that representation,
3. write the serialized graph to the specified artifact location.

The in-memory representation remains available to the next milestone.

The pipeline shall not automatically deserialize an artifact merely because
the artifact was saved.

---
## Not Saving Intermediate Output
A milestone does not save its canonical output when:
```turtle
otdd:saveIntermediate false
```
or when no init.ttl file is present.

Example:
```turtle
@prefix otdd: <https://dynamicontology.com/otdd#> .

<urn:otdd:milestone-1-init>
    a otdd:MilestoneInitialization ;
    otdd:milestone <urn:otdd:milestone-1> ;
    otdd:saveIntermediate false .
```
The resulting execution is:
```text
XML Schema
    │
    ▼
Logical Schema Model in memory
    │
    ▼
Milestone 2
```
No logical-schema.ttl artifact is written.

## Example 1 — Fast In-Memory Execution
This configuration runs the pipeline in memory and does not save the
Milestone 1 intermediate representation.

This is also the behavior when no init.ttl file is present.

```turtle
@prefix otdd: <https://dynamicontology.com/otdd#> .

<urn:otdd:execution>
    a otdd:PipelineInitialization ;
    otdd:hasMilestoneInitialization
        <urn:otdd:milestone-1-init>,
        <urn:otdd:milestone-2-init> .

<urn:otdd:milestone-1-init>
    a otdd:MilestoneInitialization ;
    otdd:milestone <urn:otdd:milestone-1> ;
    otdd:saveIntermediate false .

<urn:otdd:milestone-2-init>
    a otdd:MilestoneInitialization ;
    otdd:milestone <urn:otdd:milestone-2> ;
    otdd:inputSource otdd:InMemory .
```
Execution:
```text
XML Schema
    │
    ▼
Milestone 1
    │
    │ Logical Schema Model in memory
    ▼
Milestone 2
```
---
## Example 2 — Save the Intermediate Artifact but Continue In Memory
This configuration saves the Milestone 1 result while still passing the model
directly to Milestone 2.
```turtle
@prefix otdd: <https://dynamicontology.com/otdd#> .

<urn:otdd:execution>
    a otdd:PipelineInitialization ;
    otdd:hasMilestoneInitialization
        <urn:otdd:milestone-1-init>,
        <urn:otdd:milestone-2-init> .

<urn:otdd:milestone-1-init>
    a otdd:MilestoneInitialization ;
    otdd:milestone <urn:otdd:milestone-1> ;
    otdd:saveIntermediate true ;
    otdd:intermediateArtifact
        "docs/milestones/milestone-1/artifacts/logical-schema.ttl" .

<urn:otdd:milestone-2-init>
    a otdd:MilestoneInitialization ;
    otdd:milestone <urn:otdd:milestone-2> ;
    otdd:inputSource otdd:InMemory .
```
Execution:
```text
                         logical-schema.ttl
                        ▲
                       /
XML Schema             /
    │                 /
    ▼                /
Milestone 1──────────
    │
    │ Logical Schema Model in memory
    ▼
Milestone 2
```
This mode provides a persistent milestone artifact without requiring an
immediate reload.

It is appropriate for normal development and milestone completion.

## Example 3 — Initialize Milestone 2 from the Milestone 1 Artifact
This configuration starts Milestone 2 from the persistent Milestone 1 output.
```turtle
@prefix otdd: <https://dynamicontology.com/otdd#> .

<urn:otdd:execution>
    a otdd:PipelineInitialization ;
    otdd:hasMilestoneInitialization
        <urn:otdd:milestone-2-init> .

<urn:otdd:milestone-2-init>
    a otdd:MilestoneInitialization ;
    otdd:milestone <urn:otdd:milestone-2> ;
    otdd:inputSource otdd:IntermediateArtifact ;
    otdd:intermediateArtifact
        "docs/milestones/milestone-1/artifacts/logical-schema.ttl" .
```
Execution:
```text
docs/milestones/milestone-1/artifacts/logical-schema.ttl
    │
    ▼
Deserialize Logical Schema Model
    │
    ▼
Milestone 2
```
Milestone 1 is not executed.

This mode is useful when:

* developing Milestone 2 independently,
* reproducing a prior run,
* debugging Milestone 2,
* testing the Milestone 1–Milestone 2 contract,
* avoiding repeated schema loading.

---

## Example 4 — Verification of the Serialized Boundary

This configuration intentionally saves the Milestone 1 result and then
initializes Milestone 2 from that saved artifact.

```turtle
@prefix otdd: <https://dynamicontology.com/otdd#> .

<urn:otdd:execution>
    a otdd:PipelineInitialization ;
    otdd:hasMilestoneInitialization
        <urn:otdd:milestone-1-init>,
        <urn:otdd:milestone-2-init> .

<urn:otdd:milestone-1-init>
    a otdd:MilestoneInitialization ;
    otdd:milestone <urn:otdd:milestone-1> ;
    otdd:saveIntermediate true ;
    otdd:intermediateArtifact
        "docs/milestones/milestone-1/artifacts/logical-schema.ttl" .

<urn:otdd:milestone-2-init>
    a otdd:MilestoneInitialization ;
    otdd:milestone <urn:otdd:milestone-2> ;
    otdd:inputSource otdd:IntermediateArtifact ;
    otdd:intermediateArtifact
        "docs/milestones/milestone-1/artifacts/logical-schema.ttl" .
```

Execution:

```text
XML Schema
    │
    ▼
Milestone 1
    │
    ▼
logical-schema.ttl
    │
    ▼
Deserialize Logical Schema Model
    │
    ▼
Milestone 2
```

This mode is intentionally slower.

It verifies that:

* Milestone 1 can serialize its canonical output,
* the artifact can be read,
* the canonical model can be reconstructed,
* Milestone 2 can initialize from the milestone boundary artifact.

This is the strongest verification of the serialized contract between the two
milestones.

---

## Example 5 — Save Multiple Milestone Results

The same pattern may be extended to later milestones.

```turtle
@prefix otdd: <https://dynamicontology.com/otdd#> .

<urn:otdd:execution>
    a otdd:PipelineInitialization ;
    otdd:hasMilestoneInitialization
        <urn:otdd:milestone-1-init>,
        <urn:otdd:milestone-2-init>,
        <urn:otdd:milestone-3-init> .

<urn:otdd:milestone-1-init>
    a otdd:MilestoneInitialization ;
    otdd:milestone <urn:otdd:milestone-1> ;
    otdd:saveIntermediate true ;
    otdd:intermediateArtifact
        "docs/milestones/milestone-1/artifacts/logical-schema.ttl" .

<urn:otdd:milestone-2-init>
    a otdd:MilestoneInitialization ;
    otdd:milestone <urn:otdd:milestone-2> ;
    otdd:inputSource otdd:InMemory ;
    otdd:saveIntermediate true ;
    otdd:intermediateArtifact
        "docs/milestones/milestone-2/artifacts/ontology-model.ttl" .

<urn:otdd:milestone-3-init>
    a otdd:MilestoneInitialization ;
    otdd:milestone <urn:otdd:milestone-3> ;
    otdd:inputSource otdd:InMemory ;
    otdd:saveIntermediate false .
```

Execution:

```text
XML Schema
    │
    ▼
Milestone 1 ───────► logical-schema.ttl
    │
    ▼
Milestone 2 ───────► ontology-model.ttl
    │
    ▼
Milestone 3
```

Each milestone may independently determine whether its canonical output is
saved.

---

## Default Behavior

When `init.ttl` does not explicitly request an intermediate save, the default
or when no init.ttl file is present, shall be:

```text
saveIntermediate = false
```

When a milestone is executed as part of a continuous pipeline and no input
source is specified, the default shall be:

```text
inputSource = InMemory
```

Therefore, the default behavior favors efficient in-memory execution.

Persistent intermediate behavior must be requested explicitly.

---

## Artifact Location

A milestone initialization that saves or loads an intermediate representation
shall identify the artifact location.

Example:

```turtle
otdd:intermediateArtifact
    "docs/milestones/milestone-1/artifacts/logical-schema.ttl" .
```

Relative paths shall be resolved from the project root unless a different base
is explicitly established by the application.

An implementation may also accept file IRIs:

```turtle
otdd:intermediateArtifact
    <file:///C:/projects/uad-3-6-validation/docs/milestones/milestone-1/artifacts/logical-schema.ttl> .
```

Project-relative paths are preferred for version-controlled initialization
files because they are portable across development environments.

---

## Missing Artifact Behavior

When a milestone is configured with:

```turtle
otdd:inputSource otdd:IntermediateArtifact
```

the specified artifact must exist.

If the artifact does not exist, the pipeline shall fail with an explicit
initialization error.

The pipeline shall not silently execute the preceding milestone or substitute
an in-memory value.

For example:

```text
Milestone 2 cannot initialize.

Required intermediate artifact not found:

docs/milestones/milestone-1/artifacts/logical-schema.ttl
```

Failing explicitly preserves reproducibility and prevents an execution from
silently using a different initialization path than the one declared in
`init.ttl`.

---

## Invalid Configuration

The initialization graph shall be rejected when it contains contradictory or
incomplete instructions.

Examples include:

* loading from an intermediate artifact without specifying its location,
* saving an intermediate artifact without specifying its location,
* specifying more than one input source for the same milestone,
* referring to an unknown milestone,
* specifying an unsupported input source.

Invalid initialization shall stop pipeline execution before milestone
processing begins.

---

## Relationship to Tests

The initialization mechanism shall support tests for both execution paths.

### In-memory path

A test shall verify that Milestone 2 can consume the in-memory Logical Schema
Model produced by Milestone 1.

```text
Milestone 1 runtime model
    │
    ▼
Milestone 2
```

### Artifact path

A test shall verify that Milestone 2 can reconstruct its initial state from:

```text
docs/milestones/milestone-1/artifacts/logical-schema.ttl
```

```text
logical-schema.ttl
    │
    ▼
Milestone 2
```

### Equivalence

The Milestone 2 result shall be equivalent regardless of whether its initial
state came from:

* the in-memory Milestone 1 result, or
* the serialized Milestone 1 artifact.

This establishes that the choice of an initialization path does not change the
meaning of the transformation.

---

## Rationale

The initialization strategy is represented as knowledge rather than hidden in
application code.

This provides several advantages:

* the selected execution path is explicit,
* the configuration is version-controlled,
* pipeline executions are reproducible,
* milestone boundaries are independently testable,
* later milestones can be executed without rerunning earlier milestones,
* production execution can avoid unnecessary file operations,
* verification execution can exercise serialization boundaries.

Using RDF for initialization is consistent with the architecture of OTDD.

The pipeline configuration is itself a graph describing the intended behavior
of the transformation process.

---

## Consequences

### Advantages

* Intermediate persistence can be enabled or disabled without changing code.
* Milestone initialization can be selected independently.
* Development and production use the same transformation implementation.
* Persistent artifacts become explicit milestone interfaces.
* Individual milestones can be rerun or developed independently.
* Pipeline execution is declarative and reproducible.
* The initialization configuration can itself be validated.

### Trade-offs

* Each persistent canonical representation requires serialization and
  deserialization support.
* Artifact formats must remain compatible with their corresponding milestone.
* Verification through serialized artifacts is slower than direct in-memory
  execution.
* The pipeline must validate `init.ttl` before execution.
* In the case of no `init.ttl` file, execution takes a known, fast execution path.

---

## Implementation Boundary

This ADR defines the behavior and RDF configuration contract.

It does not prescribe:

* the Python class used to load `init.ttl`,
* the command-line interface,
* the dependency injection mechanism,
* the internal serializer implementation,
* the internal deserializer implementation.

Those are implementation details provided they preserve the behavior defined
by this decision.

---

## Related ADRs

* ADR-0003 — Generated Semantic Assets
* ADR-0006 — Ontology Test-Driven Development
* ADR-0008 — Canonical Internal Representation

---

## Decision Summary

The OTDD pipeline shall use `init.ttl` to declare how milestone boundaries are
handled.

A milestone output may be:

* retained only in memory,
* passed in memory and also saved,
* reconstructed from a previously saved intermediate artifact.

The default execution path is in memory.

Intermediate saving and artifact-based initialization must be explicitly
requested in `init.ttl`.

The result of a milestone shall have the same meaning regardless of whether it
is received directly in memory or reconstructed from its canonical persistent
artifact.