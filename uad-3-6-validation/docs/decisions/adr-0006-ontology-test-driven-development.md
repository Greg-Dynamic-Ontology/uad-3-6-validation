# ADR-0006: Ontology Test-Driven Development (OTDD)

**Status:** Accepted

## Context

The UAD 3.6 Validation project is intended to produce more than a
working ontology and validation environment. It also serves as the
reference implementation for developing and evaluating Ontology
Test-Driven Development (OTDD).

Traditional Test-Driven Development (TDD) demonstrated the value of
executable verification in software engineering. OTDD extends those
engineering principles to semantic engineering by emphasizing semantic
competencies, ontology artifacts, SHACL validation, executable
verification, and engineering traceability.

During implementation it became apparent that semantic engineering
occurs in two distinct contexts:

- **Greenfield Semantic Engineering**, where semantic competencies are
  discovered and refined during system design.
- **Harvest Semantic Engineering**, where semantic competencies are
  systematically extracted from authoritative semantic assets such as
  schemas, instance documents, implementation guides, controlled
  vocabularies, and business rules.

UAD 3.6 Validation is a Harvest Semantic Engineering project.

## Decision

The project adopts Ontology Test-Driven Development (OTDD) as its
engineering methodology.

For every semantic competency, the preferred engineering workflow is:

1. Identify the semantic competency.
2. Create representative valid and invalid example instances.
3. Execute the existing verification suite to detect regressions.
4. Execute the new competency verification and observe a RED state.
5. Implement or extend the ontology.
6. Implement or extend SHACL validation.
7. Execute the verification suite until GREEN.
8. Refactor while preserving semantic traceability.
9. Record methodology lessons when implementation reveals improvements
   to OTDD itself.

The purpose of this workflow is to preserve engineering traceability,
not to enforce process ceremony.

## Consequences

### Positive

- Establishes a repeatable engineering methodology for semantic
  engineering.
- Maintains traceability from semantic competencies through ontology,
  SHACL, examples, verification, and documentation.
- Encourages executable verification as semantic models evolve.
- Supports both Greenfield and Harvest semantic engineering projects.

### Trade-offs

- Requires additional engineering artifacts beyond the ontology itself.
- Introduces up-front effort to define competencies and verification.
- Requires discipline to maintain traceability as the implementation
  evolves.

## Relationship to UAD

UAD serves as the reference implementation for OTDD.

Implementation experience gained during UAD development is recorded in
the OTDD implementation notes and may be incorporated into the
methodology after repeated engineering experience demonstrates that the
practice is stable and broadly applicable.
