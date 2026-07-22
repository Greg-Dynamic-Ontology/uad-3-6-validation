Here is the Markdown content for `docs/architecture/uad36-ontology.md`.

# UAD 3.6 Ontology Design

## Purpose

This document explains the design of `ontology/uad36-core.ttl`.

The purpose of `uad36-core.ttl` is to define the core RDF/OWL vocabulary used to represent the UAD 3.6 specification as a graph. It does not attempt to reproduce the full UAD 3.6 schema, Appendix A mappings, Appendix H rules, or appraisal instance data directly. Instead, it defines the semantic building blocks needed to represent those assets in a governed and extensible form.

The ontology provides the vocabulary for describing:

* schema components
* XML elements and attributes
* datatypes
* controlled value sets
* XLink-style relationships
* validation rules
* validation findings
* provenance back to GSE source materials

The ontology is the conceptual foundation for generated RDF assets, GraphDB loading, validation, API responses, and future tooling.

---

## Design Scope

`uad36-core.ttl` is a lightweight ontology.

It is not intended to be a complete UAD 3.6 data model by itself.

Instead, it defines the classes and properties needed to describe generated UAD specification resources.

For example, the ontology may define:

```turtle
uad:Element
uad:Attribute
uad:DataType
uad:ValidationRule
uad:ValidationFinding
```

Generated RDF files will later contain specific instances such as:

```turtle
uad-schema:PropertyAddress
uad-rule:H-00123
uad-value:ConditionRating-C3
```

The distinction is important:

```text
ontology/uad36-core.ttl
    defines the vocabulary

generated RDF assets
    use the vocabulary
```

---

## Design Principle: Specification Model, Not Appraisal Model

The core ontology primarily describes the UAD 3.6 specification, not a single appraisal report.

It answers questions such as:

* What schema components exist?
* What controlled values are allowed?
* What rules apply?
* What source document defined a rule?
* What validation finding was produced?
* What XML or graph resource was affected?

A submitted appraisal XML package may later be converted into an instance graph, but that instance graph is separate from the ontology itself.

---

## Core Classes

The ontology should begin with a small set of durable classes.

### SchemaComponent

Represents any component derived from the UAD 3.6 XML Schema.

Subclasses may include:

* `uad:Element`
* `uad:Attribute`
* `uad:ComplexType`
* `uad:SimpleType`
* `uad:DataType`
* `uad:Enumeration`

### ControlledValue

Represents an allowed value within a controlled value set.

Controlled values may later be modeled using SKOS concepts and concept schemes.

### RelationshipPredicate

Represents a governed relationship predicate, especially those derived from XLink or Appendix A mapping requirements.

This class supports the principle:

```text
XML is a tree; the world is not.
```

Relationships between XML locations become explicit graph statements.

### ValidationRule

Represents a rule derived from Appendix H, schema constraints, Appendix A mappings, or other specification material.

A rule should be represented as a first-class graph resource, not merely as code.

### ValidationFinding

Represents the result of evaluating a validation rule against an appraisal report package or generated instance graph.

A finding should be preserved:

* rule identifier
* severity
* affected location
* observed value
* expected condition
* source rule
* source specification reference

### SpecificationSource

Represents a GSE source document, appendix, spreadsheet, schema file, or other authoritative source material.

This supports traceability from generated RDF resources back to the published GSE materials.

---

## Core Properties

The ontology should define a small number of reusable properties.

### Source and Provenance Properties

Examples:

```turtle
uad:hasSource
uad:sourceDocument
uad:sourceVersion
uad:sourceLocation
uad:generatedAt
```

These properties support traceability from generated graph resources to the original GSE materials.

### Schema Relationship Properties

Examples:

```turtle
uad:hasElement
uad:hasAttribute
uad:hasDataType
uad:hasControlledValue
```

These properties describe relationships among schema-derived resources.

### Rule Properties

Examples:

```turtle
uad:appliesTo
uad:hasSeverity
uad:hasRuleExpression
uad:hasMessageTemplate
uad:appliesToGSE
```

These properties describe validation rules and how they are applied.

### Finding Properties

Examples:

```turtle
uad:triggeredByRule
uad:affectsResource
uad:affectedXmlLocation
uad:observedValue
uad:expectedValue
uad:hasExplanation
```

These properties describe validation outcomes.

---

## Relationship to SKOS

Controlled vocabularies and enumerated values should use SKOS where appropriate.

The core ontology may define UAD-specific concepts such as `uad:ControlledValue`, while generated vocabulary files may represent actual value sets as SKOS concept schemes.

Example:

```turtle
uad-value:ConditionRating
    a skos:ConceptScheme ;
    skos:prefLabel "Condition Rating" .

uad-value:C3
    a skos:Concept ;
    skos:inScheme uad-value:ConditionRating ;
    skos:prefLabel "C3" .
```

This approach keeps value sets queryable, label-friendly, and extensible.

---

## Relationship to SHACL

`uad36-core.ttl` is not a SHACL shapes file.

The ontology defines the vocabulary.

SHACL shapes may later use that vocabulary to validate generated appraisal instance graphs.

This gives the project a clean separation:

```text
OWL/RDF ontology
    defines concepts and relationships

SHACL shapes
    define validation constraints

SPARQL/Python
    handle complex rules and orchestration
```

---

## Relationship to GraphDB

GraphDB is a repository and query platform.

The ontology should not depend on GraphDB-specific features.

The intended flow is:

```text
ontology/uad36-core.ttl
        ↓
generated RDF assets
        ↓
GraphDB repository
        ↓
API and validation services
```

This keeps the model portable.

---

## Relationship to OTK

The ontology should be designed so that OTK can eventually generate, validate, or manage it.

However, the first version should be authored manually to make the design choices explicit.

OTK can later automate the trail once the trail is known.

---

## File Placement

Recommended project structure:

```text
ontology/
    uad36-core.ttl

docs/
    architecture/
        uad36-ontology.md
```

The Markdown document explains the design.

The Turtle file contains the machine-readable ontology.

---

## Initial Modeling Strategy

The first version of `uad36-core.ttl` should remain intentionally small.

It should define:

* core classes
* core properties
* labels
* comments
* basic subclass relationships
* basic property domains and ranges where helpful

It should avoid premature complexity.

Do not begin by modeling every UAD schema element manually.

Instead, define the vocabulary that generated schema resources will use later.

---

## Open Design Questions

The following questions should be resolved before large-scale RDF generation begins:

1. What project namespace should be used for the UAD 3.6 ontology?
2. What IRI pattern should be used for generated schema components?
3. How should GSE-specific differences be represented?
4. Should Appendix H rules be represented in RDF only, SHACL only, or both?
5. How should XML IDs and XML paths be mapped to stable IRIs?
6. How should XLink relationships be represented as RDF predicates?
7. How should the generated resources preserve source row, section, or page references?
8. Which assets are hand-authored and which are generated?

---

## Summary

`ontology/uad36-core.ttl` is the seed ontology for the UAD 3.6 validation project.

It defines the semantic vocabulary used to describe the UAD 3.6 specification, generated RDF resources, validation rules, findings, and provenance.

The ontology should remain small, stable, and implementation-independent.

Generated RDF, SHACL shapes, GraphDB repositories, and API services should build upon it rather than replace it.
