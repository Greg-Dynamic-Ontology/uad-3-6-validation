# Architecture Decision Records (ADRs)

This directory contains the Architecture Decision Records (ADRs) for the
UAD 3.6 Validation project.

ADRs document significant architectural and engineering decisions that
shape the project. Each ADR records the context, the decision that was
made, and the consequences of that decision. Once accepted, ADRs provide
a historical record of why the project evolved as it did.

The UAD 3.6 Validation project also serves as the reference
implementation for Ontology Test-Driven Development (OTDD). Accordingly,
some ADRs establish engineering principles that support both the UAD
implementation and the evolving OTDD methodology.

Current ADRs:

- **ADR-0001** — Project Namespace
- **ADR-0002** — IRI Minting Policy
- **ADR-0003** — Generated Semantic Assets
- **ADR-0004** — Meaning-First Ontology Development
- **ADR-0005** — Single Logical Ontology
- **ADR-0006** — Ontology Test-Driven Development (OTDD)
- **ADR-0007** — SHACL Validation Without Inference

## Relationship to Other Documentation

The project documentation is organized into three complementary areas:

- **Architecture** documents describe the semantic design and structure
  of the UAD 3.6 Validation project.
- **Architecture Decision Records (ADRs)** capture stable engineering
  and architectural decisions.
- **OTDD documentation** records the application and evolution of the
  Ontology Test-Driven Development methodology as exercised by the UAD
  reference implementation.

Implementation lessons that refine OTDD are intentionally recorded in
the OTDD documentation rather than in ADRs. When repeated engineering
experience demonstrates that a lesson has become stable, it may be
promoted into an ADR or the formal OTDD methodology.

As the project evolves, new ADRs may be added. Existing ADRs are not
rewritten to hide history; instead, subsequent ADRs supersede or refine
earlier decisions when necessary.
