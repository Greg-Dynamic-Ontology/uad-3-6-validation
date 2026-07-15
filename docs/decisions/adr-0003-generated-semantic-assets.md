# ADR-0003: Generated Semantic Assets

**Status:** Accepted

## Context

The UAD 3.6 Validation project is founded on existing, authoritative
semantic assets rather than creating a new appraisal vocabulary.

Numerous ontology artifacts can be generated deterministically from
those semantic assets. Automating their creation improves consistency,
repeatability, and traceability while reducing manual effort.

Semantic assets available for harvesting include:

- XML Schema (XSD)
- XLink relationship definitions
- XML instance documents
- Controlled vocabularies and code lists
- Implementation Guide
- Business rules

Different generators may consume different semantic assets, but all
generated artifacts remain traceable to their authoritative source.

## Decision

Semantic artifacts that can be generated deterministically shall be
generated rather than maintained manually.

Examples include:

- Predicate vocabulary generated from XLink arcroles.
- SKOS concept schemes generated from controlled vocabularies.
- Ontology class scaffolding generated from XML Schema.
- Competency inventories harvested from authoritative semantic assets.
- Future semantic assets determined to be algorithmically derivable.

Hand-authored artifacts shall focus on semantic meaning and engineering
intent rather than repetitive structural definitions.

## Consequences

### Positive

- Eliminates repetitive manual modeling.
- Ensures consistency across generated artifacts.
- Preserves traceability from generated artifacts back to their
  authoritative semantic sources.
- Simplifies regeneration when the underlying standard changes.
- Allows engineering effort to concentrate on semantic interpretation
  rather than mechanical translation.

### Trade-offs

- Requires generator software to be maintained.
- Generator behavior becomes part of the engineering baseline and must
  be verified.
- Some semantic concepts still require engineering judgment and cannot
  be generated automatically.

## Relationship to OTDD

Generated semantic assets participate fully in Ontology Test-Driven
Development (OTDD).

Automatically generated artifacts are verified in the same manner as
hand-authored artifacts. Generation reduces manual effort but does not
reduce the need for semantic validation, executable verification, or
engineering traceability.

The objective is deterministic generation followed by deterministic
verification.
