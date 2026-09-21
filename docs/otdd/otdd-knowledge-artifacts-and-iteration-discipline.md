# OTDD Knowledge Artifacts and Iteration Discipline

> **Status:** Working design guidance
>
> This document records an emerging Ontology Test-Driven Development (OTDD)
> practice developed through the UAD 3.6 Validation project. It is intended for
> reuse beyond UAD and may evolve as the methodology is applied in other
> Ontology Workbench (OWB) projects.

## Purpose

OTDD and traditional Test-Driven Development (TDD) use the same basic
engineering discipline: establish a failing test, make the smallest change
that satisfies it, refactor without changing the result, and run regression
tests. They do not, however, test or produce the same kinds of artifacts.

OTDD tests governed knowledge. Python TDD tests procedural software behavior.
Keeping those responsibilities distinct makes failures understandable and
preserves traceability from business meaning to knowledge and then to code.

This document defines:

- what counts as a governed knowledge artifact;
- why constraints and configurations are both knowledge;
- how OTDD differs from Python TDD;
- how feature files and iteration identifiers are assigned;
- how the OTDD red-green-refactor cycle is performed; and
- where later software implementation begins.

## Core Principle

> If a declarative change alters what the service knows, permits, requires, or
> considers applicable without requiring a procedural code change, that change
> is governed knowledge.

Governed knowledge is represented with explicit meaning, identity,
relationships, provenance, and lifecycle. In an RDF-based system, it belongs
in the connected RDF knowledge graph rather than in an application-specific
tree or an ungoverned configuration file.

OTDD establishes and tests that knowledge before software code is asked to
consume or enforce it.

## Knowledge Artifacts

Constraints are knowledge artifacts, but they are not the only knowledge
artifacts. The following concerns may all be governed knowledge.

| Knowledge concern | Examples | Why it is knowledge |
| --- | --- | --- |
| Ontology | Classes, properties, relationships, datatypes | Defines the concepts and relationships the system understands |
| Reference vocabulary | Statuses, roles, severity levels, authority types | Gives stable identities and meanings to controlled terms |
| Constraint | SHACL shapes, accepted-value rules, cardinality, messages | States what must, may, or must not be true |
| Constraint-set release | Set identity, authority-issued release, effective dates | Governs a versioned collection of constraints |
| Governed configuration or profile | Selected constraint sets, applicability profile, permitted composition | Declares which governed knowledge applies in a defined context |
| Applicability and authority policy | Issuer, protected set, overlay relationship, effective scope | Determines when knowledge applies and which authority governs it |
| Declarative mapping | XML-to-RDF mapping, source-field mapping, term alignment | States how one representation corresponds to another |
| Provenance | Source document, spreadsheet row, issuer, digest, governing decision | Explains where knowledge came from and why it is trusted |
| Presentation knowledge | Governed labels, explanations, audience-specific messages | Expresses how domain meaning is communicated without embedding it in code |

These are knowledge *concerns*, not isolated semantic layers. A constraint may
refer directly to an ontology property, a configuration may select a
constraint-set release, and a validation result may refer to the exact
constraint definition that produced it.

### Configurations Are Knowledge When They Express Domain Policy

A governed configuration is not merely a bag of application settings. It is a
knowledge artifact when it declares a reusable domain decision such as:

- one of several governed base constraint sets must be selected;
- multiple lender or AMC overlays may be selected;
- a selected overlay applies only to a defined program, product, or period;
- one constraint-set release requires or overlays another;
- an overlay must not weaken a protected requirement; or
- a particular governed profile is approved for a named business context.

Such a configuration needs the same qualities as other governed knowledge:
stable RDF identity, type, name, provenance, version or lifecycle status, and
explicit relationships to the resources it configures.

The fact that configuration knowledge may be serialized in Turtle, TriG,
JSON-LD, or another format does not make the serialization its identity. The
RDF resources and their IRIs carry identity and meaning.

### What Is Not a Governed Knowledge Artifact

Not every value called a configuration belongs in the knowledge graph.
Examples that normally remain outside governed domain knowledge include:

- database connection strings;
- credentials, keys, and secrets;
- server ports and process settings;
- retry counts and infrastructure timeouts;
- temporary cache state;
- a customer's current transaction or validation-cycle state; and
- procedural algorithms implemented in Python.

A transaction can *reference* governed configuration knowledge without
becoming that knowledge. For example, a validation cycle may record which
governed configuration and constraint-set releases it used. The cycle is
operational state; the reusable configuration it identifies is governed
knowledge.

## RDF Is Connected; Files Are Packaging

An RDF dataset is not a JSON or YAML tree. Governed resources must be able to
refer to one another by stable IRI across files and named graphs.

Files and directories are useful for source control, review, transport,
publication, and deployment. Named graphs are useful for provenance,
versioning, access control, lifecycle, and rollback. Neither a path nor a
named-graph boundary defines the semantic identity of a constraint,
configuration, authority, release, or ontology term.

This leads to four design rules:

1. Give every governed resource that must be referenced a stable RDF IRI.
2. Express relationships as RDF statements, not as directory placement or
   filename conventions.
3. Preserve links across named graphs and transport files.
4. Treat an executable validation graph as a purpose-specific view of governed
   knowledge, not as a second authority or identity system.

## Keep Identity Dimensions Separate

Several identifiers may occur near one constraint. They must not be
conflated.

| Identifier | Identifies |
| --- | --- |
| Constraint ID | A governed requirement, such as a source Message ID |
| Data-point ID | The governed domain term or source data point targeted by a constraint |
| Constraint-set ID | A named collection of governed constraints |
| Constraint-set release ID | An authority-issued version of that set |
| Source artifact digest | The authoritative input bytes used to derive knowledge |
| RDF transport digest | The exact bytes of a transported RDF serialization |
| Schema or specification build ID | A published technical build of the governing specification |
| Service build ID | A build of the software that consumes governed knowledge |
| Iteration ID | A development-work identifier used for traceability |

For example, an authority-issued release such as `1.5` is meaningful only in
the scope of its identified constraint set and issuing authority. It is not a
Python service build, a schema build, a constraint ID, or an `IT-nn`
identifier.

One service build should be able to consume different properly shaped and
approved constraint and configuration artifacts without constraint-specific
code changes.

## OTDD and Python TDD Are Separate Test Disciplines

| Concern | OTDD | Python TDD |
| --- | --- | --- |
| Subject under test | Meaning and governed RDF relationships | Procedural software behavior |
| Primary production artifacts | RDF/OWL, SHACL, SKOS, governed examples | Python modules and services |
| Typical test evidence | SHACL results, SPARQL competency questions, graph comparison, required entailments | Pytest assertions, fakes, mocks, integration results |
| Typical failure | Missing or incorrect identity, relationship, applicability, provenance, or constraint semantics | Incorrect control flow, state transition, persistence, API, or error handling |
| Green change | Minimal change to governed knowledge or its shapes | Minimal change to Python implementation |
| Regression suite | Complete knowledge-test suite | Complete pytest suite |

Python may be used as a transparent test runner for RDF tools, but that does
not turn a software assertion into an ontology test. The decisive question is
what the test proves. Confirming that a Turtle file parses, contains selected
text, or was loaded by Python does not prove its intended meaning.

Likewise, a SHACL shape should not be used to hide an untested procedural
algorithm. OTDD proves the declarative model. Later TDD proves that software
loads, selects, executes, persists, and reports against that model correctly.

## Iteration and Feature-File Discipline

An iteration identifier establishes a traceability boundary.

1. An `IT-nn` identifier is bound to one feature file or to an explicitly
   associated set of feature files.
2. A feature file belongs to exactly one iteration.
3. A feature file must never be reused by another iteration.
4. All feature files associated with one iteration must use the same test
   discipline.
5. An iteration must not mix OTDD rules and scenarios with Python TDD rules
   and scenarios.

The fifth rule is especially important. Similar Gherkin wording can conceal
two different engineering activities.

### OTDD Iteration

An OTDD iteration may define and test:

- the RDF identity and type of a governed configuration;
- relationships among a configuration, authorities, constraint sets, and
  releases;
- SHACL requirements for a conforming constraint artifact;
- applicability and must-not-weaken relationships;
- the semantic families used to compare constraint strength; or
- the provenance required for a governed decision.

Its green artifacts are knowledge artifacts and knowledge tests.

### Python TDD Iteration

A later Python TDD iteration may define and test:

- loading RDF transport artifacts;
- verifying a content digest;
- staging and atomically activating a dataset;
- selecting effective constraints for a validation cycle;
- invoking a SHACL processor;
- persisting governance decisions; or
- returning validation findings through an API.

Its green artifacts are executable software and pytest tests.

If one business capability requires both, it is implemented as at least two
iterations: an OTDD iteration establishing the knowledge contract, followed
by one or more TDD iterations implementing software against that contract.
The shared business capability provides continuity; the iteration identifiers
keep the evidence honest.

## OTDD Red-Green-Refactor

### 1. Establish the Semantic Competency

State what must be knowable or verifiable. A competency question should ask
about domain meaning, not a file layout or implementation detail.

Examples:

- Which constraint-set release does this configuration select?
- Which authority issued this release?
- Which protected constraint does this proposed refinement affect?
- Can the provenance of this executable shape be traced to its source row?

### 2. Red

Create representative RDF examples and an executable knowledge test that
demonstrates the missing or incorrect meaning.

A red OTDD test may be:

- a valid example that fails the current SHACL model;
- an invalid example that incorrectly conforms;
- a SPARQL `ASK` competency question that returns the wrong result;
- a SPARQL query whose expected bindings are absent or wrong;
- a graph-equivalence test that exposes duplicate identity; or
- a reasoning test when entailment itself is the subject under test.

The failure, fixture, expected result, and command used to run it must be
visible and reproducible by the team.

### 3. Green

Make the smallest change to the ontology, shapes, vocabulary, governed
configuration, mapping, or example data that satisfies the semantic
competency. Do not add procedural application behavior to make an OTDD test
green.

Unless inference is explicitly under test, SHACL validation evaluates the
explicit RDF graph without inference.

### 4. Refactor

Improve names, factor reusable shapes, remove accidental duplication, or
clarify relationships while preserving IRIs, intended meaning, provenance,
and all knowledge-test results.

### 5. Regression

Run the complete knowledge-test suite. Focused tests are useful during the
cycle, but completion requires the full suite so that a local model change
cannot silently alter another competency.

Run the Python regression suite separately when software artifacts were also
changed. Report the two results separately; do not combine their counts as if
they were one test population.

## Strengthening and Weakening as Knowledge

Supplemental investor, government-program, AMC, lender, or other governed
constraints may strengthen applicable protected requirements but must not
weaken them.

Under the same applicability conditions, constraint B is at least as strong
as constraint A if B does not allow anything that A would reject.

Constraint B strictly strengthens constraint A if B also rejects at least one
case that A would allow.

In RDF terms, every report graph that conforms to B must also conform to A. B
must remain satisfiable; a contradictory constraint is an error, not a
stronger constraint.

For a simple value constraint, this reduces to accepted-value inclusion: the
values accepted by B are a subset of those accepted by A. The subset is proper
when B strictly strengthens A.

Examples include:

- a higher minimum strengthens a lower minimum;
- a lower maximum strengthens a higher maximum;
- a subset of allowed values strengthens a larger allowed set;
- a higher `minCount` strengthens a lower `minCount`;
- a lower `maxCount` strengthens a higher `maxCount`; and
- equivalent-or-stronger enforcement over additional cases strengthens a
  requirement, while excluding previously covered cases weakens it.

An independent new requirement is additive rather than a refinement. A
refinement must identify the protected constraint it affects. Authority and
protection are expressed through governed RDF relationships; they are not
inferred from names such as “GSE,” “lender,” or “AMC,” nor from filenames or
loading order.

If strength cannot be proven for a semantic family, the relationship requires
governance review and remains inactive until an authorized decision identifies
the evidence and scope. A weakening refinement is rejected rather than
silently ignored.

OTDD establishes these concepts, identities, relationships, and conformance
rules. A later Python TDD iteration implements any runtime comparison,
activation, rejection, and reporting behavior.

## Illustrative RDF Relationship

The following abbreviated Turtle is illustrative, not a final vocabulary:

```turtle
@prefix ex:  <https://example.org/knowledge/> .
@prefix gov: <https://example.org/governance/> .

ex:configuration/acme-conventional-2026
    a gov:ValidationConfiguration ;
    gov:name "Acme conventional appraisal validation" ;
    gov:selectsConstraintSetRelease ex:release/gse-uad-3.6 ;
    gov:selectsConstraintSetRelease ex:release/acme-overlay-2026-01 .

ex:release/acme-overlay-2026-01
    a gov:ConstraintSetRelease ;
    gov:releaseOf ex:constraint-set/acme-overlay ;
    gov:overlays ex:release/gse-uad-3.6 ;
    gov:mustNotWeaken ex:release/gse-uad-3.6 .

ex:definition/acme-ltv-min-2026-01
    a gov:ConstraintDefinition ;
    gov:definesCanonicalConstraint ex:constraint/acme-ltv-min ;
    gov:refines ex:constraint/gse-ltv-min ;
    gov:inRelease ex:release/acme-overlay-2026-01 .
```

The configuration, releases, and constraint definitions remain independently
identified and connected. Their filenames and named-graph placement may
change without changing these relationships.

## Definition of Ready for an OTDD Iteration

Before beginning an OTDD iteration, confirm that:

- the business meaning and authoritative evidence are identified;
- the semantic competency or competency questions are stated;
- the governed resource identities are distinguishable;
- representative valid and invalid RDF examples can be created;
- the intended test mechanism is identified;
- the feature file contains only OTDD work; and
- the feature file is assigned to no other iteration.

## Definition of Done for an OTDD Iteration

An OTDD iteration is complete when:

- every scenario has visible red evidence followed by green evidence;
- all required identities and relationships are represented in RDF;
- the governed artifacts conform to their shapes;
- competency questions return their expected results;
- provenance and applicability remain queryable;
- the complete knowledge regression suite passes;
- the result does not depend on serialization order, filename, or directory;
- no procedural Python behavior has been included under the iteration; and
- the artifacts and test commands are available for independent review.

## Application to Constraint Design

For constraint work, a clean sequence is:

1. Use an OTDD iteration to define the RDF family for constraint sets,
   releases, definitions, configurations, provenance, and cross-resource
   references.
2. Use a separate OTDD iteration to define additive, refining,
   strengthening, weakening, applicability, and governed-review knowledge.
3. Use later Python TDD iterations to implement loading, catalogs, staging,
   activation, runtime comparison, composition, and enforcement.

This separation does not create disconnected models. It creates explicit
contracts between connected governed knowledge and the software that operates
on it.

## Related Project Guidance

- [Ontology Test-Driven Development flow](../methodology/otdd-development-flow.md)
- [ADR-0006: Ontology Test-Driven Development](../decisions/adr-0006-ontology-test-driven-development.md)
- [ADR-0007: SHACL validation without inference](../decisions/adr-0007-shacl-validation-without-inference.md)
- [ADR-0018: Organize OWB as connected knowledge concerns](../decisions/adr-0018-organize-owb-as-connected-knowledge-concerns.md)

## Summary

OTDD is not TDD performed on a Turtle filename. It is executable verification
of governed meaning.

Constraints are knowledge. Governed configurations are knowledge. Ontologies,
vocabularies, mappings, applicability, authority, and provenance may also be
knowledge. Runtime settings, transaction state, and procedural algorithms are
not automatically knowledge merely because they affect execution.

By assigning OTDD and Python TDD to separate iterations and feature files, the
project can show exactly when meaning became correct and exactly when software
learned to use it.
