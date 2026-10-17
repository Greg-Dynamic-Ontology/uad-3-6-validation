# Architecture Decision Records (ADRs)

This directory contains the Architecture Decision Records (ADRs) for the UAD
3.6 Validation project.

ADRs document significant architectural and engineering decisions that shape the
project. 
Each ADR records its context, decision, and consequences.
Accepted ADRs provide a historical record of why the project evolved as it did.

The UAD 3.6 Validation project also serves as a reference implementation for
Ontology Test-Driven Development (OTDD).
Some ADRs therefore establish engineering practices that support both the UAD
implementation and the evolving OTDD methodology.

## Current ADRs

- [ADR-0001 — Project Namespace](adr-0001-project-namespace.md)
- [ADR-0002 — IRI Minting Policy](adr-0002-iri-minting-policy.md)
- [ADR-0003 — Generated Semantic Assets](adr-0003-generated-semantic-assets.md)
- [ADR-0004 — Meaning-First Ontology Development](adr-0004-meaning-first-ontology-development.md)
- [ADR-0005 — Single Logical Ontology](adr-0005-single-logical-ontology.md)
- [ADR-0006 — Ontology Test-Driven Development (OTDD)](adr-0006-ontology-test-driven-development.md)
- [ADR-0007 — SHACL Validation Without Inference](adr-0007-shacl-validation-without-inference.md)
- [ADR-0008 — Canonical Internal Representation](adr-0008-canonical-internal-representation.md)
- [ADR-0009 — Vendor Artifact Preservation](adr-0009-uad-sample-artifact-policy.md)
- [ADR-0010 — Role-Based User Experience](adr-0010-role-based-user-experience.md)
- [ADR-0011 — Knowledge-Centric User Interface](adr-0011-knowledge-centric-user-interface.md)
- [ADR-0012 — Validation-Derived Analytics and AI Assistance](adr-0012-validation-derived-analytics-and-ai-assistance.md)
- [ADR-0013 — UAD Validation Pipeline](adr-0013-uad-validation-pipeline.md)
- [ADR-0014 — RDF Representation of XML Schema Components](adr-0014-rdf-representation-of-xml-schema-components.md)
- [ADR-0015 — SHACL Representation of XML Schema Components](adr-0015-shacl-representation-of-xml-schema-components.md)
- [ADR-0016 — Schema Loader Modularization](adr-0016-schema-loader-modularization.md)
- [ADR-0017 — IRI and Collision Policy](adr-0017-IRI-and-collision-policy.md)
- [ADR-0018 — Organize OWB as Connected Knowledge Concerns](adr-0018-organize-owb-as-connected-knowledge-concerns.md)
- [ADR-0019 — Recover the Regression Baseline Without Rewriting IT History](adr-0019-regression-recovery-without-rewriting-it-history.md)

## Relationship to Other Documentation

The project documentation has complementary roles:

- **Architecture documentation** describes the semantic design and structure of
the project.
- **ADRs** record stable architectural and engineering decisions.
- **OTDD documentation** records how Ontology Test-Driven Development is applied
and refined through the reference implementation.

Implementation lessons that refine OTDD belong in OTDD documentation.
When experience establishes a stable architectural or engineering decision, a
later ADR may record it.

ADRs are historical records. When a decision changes, a later ADR should
supersede or refine the earlier one rather than rewriting it to hide the history.