# ADR-0004: Meaning-First Ontology Development

**Status:** Accepted

## Context

The UAD 3.6 Validation project is not developing a new appraisal
standard. It is engineering a semantic representation of an existing,
authoritative standard.

The business meaning of UAD is distributed across multiple semantic
assets rather than residing in any single artifact. These assets include:

- XML Schema (XSD)
- XML instance documents
- Implementation Guide
- Business rules
- Controlled vocabularies
- XLink relationship definitions

Each contributes part of the semantic model. No single artifact is
sufficient to derive the complete ontology.

Consequently, ontology development must begin with business meaning and
semantic intent rather than with XML structure alone.

## Decision

The project adopts a **Meaning-First** approach.

Semantic concepts and relationships shall be identified from the
combined semantic assets before they are represented in OWL, SHACL, or
other implementation artifacts.

The engineering sequence is:

Business Semantic Assets
→ Semantic Analysis
→ Meaning Model
→ Ontology
→ SHACL Shapes
→ Instance Validation
→ Measurements

XML Schema and XML instance documents are treated as semantic sources,
not as the ontology itself.

## Consequences

### Positive

- Preserves business meaning independently of XML serialization.
- Allows multiple implementation projections (XML, RDF, JSON-LD, etc.)
  from a single semantic model.
- Enables systematic harvesting of semantic competencies from existing
  standards.
- Supports validation of instance documents against semantic intent,
  rather than structural correctness alone.

### Trade-offs

- Requires analysis of multiple semantic assets rather than relying
  solely on schema structure.
- Increases early modeling effort in exchange for improved semantic
  traceability and long-term maintainability.

## Relationship to OTDD

This ADR establishes the semantic foundation for Ontology Test-Driven
Development (OTDD).

In Harvest Semantic Engineering projects such as UAD 3.6 Validation,
semantic competencies are derived from authoritative semantic assets,
implemented within the ontology, verified through SHACL and executable
tests, and traced back to their original business meaning.
