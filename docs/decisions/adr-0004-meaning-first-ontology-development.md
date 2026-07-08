# Architecture Decision Record 0004: Meaning-First Ontology Development

**Status:** Accepted

**Date:** 2026-07-03

## Context

The Uniform Appraisal Dataset (UAD) 3.6 is a domain-specific specialization of
the MISMO 3.6 Reference Model developed by Fannie Mae and Freddie Mac for the
exchange of residential real estate appraisal information.

Rather than defining an entirely new data model, UAD constrains and specializes
the broader MISMO reference model through additional implementation guidance,
controlled vocabularies, business rules, and appraisal-specific semantics.

The objective of the UAD 3.6 Validation project is not simply to validate UAD
XML instance documents against the UAD XML Schema.

XML Schema validation determines whether an instance document conforms to the
syntactic constraints expressed by the schema. While necessary, schema
validation alone cannot determine whether an appraisal expresses complete,
consistent, or meaningful business information.

The business meaning of UAD is distributed across multiple artifacts.

The MISMO 3.6 Reference Model provides the general data vocabulary and
structural framework.

The UAD Implementation Guide specifies how that vocabulary is constrained,
interpreted, and applied to residential appraisal reporting.

Accepted appraisal practice supplies additional concepts and relationships that
are assumed by professional appraisers but are not explicitly represented in
either the XML Schema or the Implementation Guide.

The XML Schema is therefore viewed as an **exchange projection** of an
underlying conceptual ontology rather than as the ontology itself.

The purpose of this project is to reconstruct that conceptual ontology so that
UAD instance documents can be interpreted semantically rather than merely
validated syntactically.

Once represented as RDF, appraisal information can be validated using SHACL,
queried using SPARQL, measured using graph algorithms, and reasoned over by AI
systems.

## Decision

The UAD project shall adopt a **Meaning-First** approach to ontology
development.

Business concepts shall be identified from:

- the MISMO 3.6 Reference Model;
- the UAD Implementation Guide;
- accepted appraisal practice;
- the MISMO Logical Data Dictionary (LDD);
- and the relationships expressed within UAD instance documents.

The ontology shall model:

- appraisal concepts;
- business relationships;
- valuation reasoning;
- evidence;
- business semantics;

rather than XML elements, XML attributes, or document structure.

The XML Schema shall be treated as an implementation artifact used for data
exchange rather than as the authoritative semantic model.

## Design Principle

> **The data model is just the carrier. The meaning is in the implementation
> guide.**

The ontology captures business meaning independently of any particular
serialization.

## Projection Families

The project recognizes multiple projections of the same underlying conceptual
ontology.

### Documentation Projection

Human-readable descriptions of the domain.

Examples include:

- Meaning Models
- Architecture documents
- Architecture Decision Records (ADRs)

### Semantic Projection

Machine-processable representations of meaning.

Examples include:

- RDF
- RDFS
- OWL
- SKOS

### Constraint Projection

Formal validation rules governing semantic correctness.

Examples include:

- SHACL
- Business rule ontologies

### Exchange Projection

Representations optimized for interchange between systems.

Examples include:

- MISMO XML
- JSON
- JSON-LD

### Analytics Projection

Representations supporting measurement, reasoning, and analysis.

Examples include:

- SPARQL
- Graph algorithms
- Validation reports
- Quality metrics
- AI prompts

These projections represent different views of the same conceptual ontology.
They are not independent models.

## Consequences

Ontology development begins with business meaning rather than XML structures.

Automatic ontology generation from XML Schema remains valuable because it
recovers structural information from the MISMO reference model.

However, generated ontology artifacts are considered inputs to ontology
development rather than the completed ontology.

The completed ontology incorporates both structural information recovered from
MISMO and business semantics reconstructed from the UAD Implementation Guide and
accepted appraisal practice.

This approach allows:

- semantic validation independent of XML syntax;
- multiple serializations from a single conceptual model;
- graph-based business rule validation;
- competency-question driven development;
- graph measurements;
- AI reasoning over appraisal knowledge;
- future support for additional exchange formats without redesigning the
  ontology.

## Development Process

New concepts should normally be developed using the following workflow.

1. Identify the business concept.
2. Document the concept in the Meaning Model.
3. Write failing ontology tests.
4. Extend the ontology.
5. Create example RDF.
6. Add SHACL constraints where appropriate.
7. Verify competency questions using SPARQL.
8. Define measurements supported by the concept.

## Alternatives Considered

### XML-First Development

Rejected.

An XML-first approach couples business meaning to a particular serialization and
makes semantic reasoning unnecessarily difficult.

### Schema-First Ontology Generation

Partially accepted.

Automatic ontology generation is valuable for recovering structural information
contained within the MISMO XML Schema.

However, the generated ontology cannot capture the business semantics expressed
within the UAD Implementation Guide or accepted appraisal practice.

Generated ontology artifacts therefore become inputs to Meaning-First ontology
development rather than the final semantic model.

## Related ADRs

- ADR 0001 — Project Namespace
- ADR 0002 — IRI Minting Policy
- ADR 0003 — Generated Semantic Assets