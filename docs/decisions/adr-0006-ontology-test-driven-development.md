# Architecture Decision Record 0006: Ontology Test-Driven Development

**Status:** Accepted

**Date:** 2026-07-03

## Context

The UAD 3.6 Validation project is developing a conceptual ontology that serves
as the semantic foundation for validation, measurement, reasoning, and future
AI-assisted analysis.

Unlike traditional software projects, the primary deliverable is not executable
code but a collection of semantic artifacts including:

- Meaning Models;
- RDF/OWL ontologies;
- generated semantic assets;
- SHACL constraints;
- SPARQL queries;
- measurement definitions;
- example instance documents.

These artifacts collectively define the semantic behavior of the system.

Consequently, ontology development should be subject to the same engineering
discipline traditionally applied to software development.

## Decision

The project shall adopt **Ontology Test-Driven Development (OTDD).**

Every significant addition to the conceptual model shall be accompanied by one
or more automated regression tests before the ontology implementation is
considered complete.

Tests are considered first-class project artifacts.

A concept is not considered complete until both its semantic representation and
its corresponding tests have been implemented.

## Development Workflow

New concepts should normally be developed using the following workflow.

1. Identify the business concept.
2. Describe the concept in the Meaning Model.
3. Write one or more failing ontology tests.
4. Extend the ontology.
5. Create or update example RDF instances.
6. Add SHACL constraints where appropriate.
7. Verify competency questions using SPARQL.
8. Define measurements supported by the concept.
9. Execute the complete regression test suite.

The order may vary for small refactorings, but all completed concepts should
satisfy this workflow.

## Types of Tests

The regression suite may include several categories of tests.

### Documentation Tests

Verify that required architectural and semantic documentation exists.

Examples include:

- Meaning Model sections;
- ADRs;
- architecture documents.

### Ontology Structure Tests

Verify the ontology itself.

Examples include:

- ontology parses successfully;
- ontology declaration exists;
- namespace bindings are correct;
- required classes exist;
- required properties exist;
- labels exist;
- definitions exist.

### Semantic Integrity Tests

Verify the conceptual model.

Examples include:

- domains and ranges;
- subclass relationships;
- property characteristics;
- vocabulary alignment.

### Example Instance Tests

Verify that example RDF instance documents are valid representations of the
ontology.

### SHACL Validation Tests

Verify that semantic constraints accept valid data and reject invalid data.

### SPARQL Competency Tests

Verify that competency questions can be answered using SPARQL.

Competency questions demonstrate that the ontology supports its intended use.

### Measurement Tests

Verify that required quality measurements can be computed from RDF instance
documents.

## Philosophy

Testing is not limited to executable Python code.

Meaning Models, ontologies, RDF examples, SHACL constraints, SPARQL queries,
and generated semantic assets are all software artifacts whose correctness can
be verified automatically.

The regression suite therefore validates both implementation and semantics.

## Consequences

Every ontology enhancement should include corresponding regression tests.

Changes to the conceptual model should cause regression failures whenever they
introduce inconsistencies.

The regression suite becomes an executable specification of the ontology.

A passing regression suite provides confidence that semantic evolution has not
broken previously established meaning.

## Current Practice

The project currently uses `pytest` as the primary regression framework.

Current tests include verification of:

- ontology existence;
- Turtle syntax;
- namespace policy;
- ontology declarations;
- required classes;
- required object properties;
- labels;
- definitions;
- ontology organization;
- documentation consistency;
- generated semantic assets.

Additional test categories will be added as SHACL constraints, SPARQL
competency questions, measurements, and ontology alignment layers are
introduced.

## Alternatives Considered

### Documentation-Only Development

Rejected.

Documentation alone cannot guarantee that semantic artifacts remain internally
consistent as the ontology evolves.

### Code-Only Testing

Rejected.

The ontology itself is a primary software artifact and therefore requires direct
regression testing independent of application code.

## Related ADRs

- ADR 0001 — Project Namespace
- ADR 0002 — IRI Minting Policy
- ADR 0003 — Generated Semantic Assets
- ADR 0004 — Meaning-First Ontology Development
- ADR 0005 — Single Logical Ontology