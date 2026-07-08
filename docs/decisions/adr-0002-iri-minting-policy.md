# Architecture Decision Record 0002: IRI Minting Policy

**Status:** Accepted

**Date:** 2026-06-26

## Context

The UAD 3.6 Validation project represents GSE specifications, generated RDF assets, 
appraisal instance graphs, validation rules, and validation findings as RDF resources.

Every RDF resource requires a stable identifier.

The identifier must remain independent of:

* repository layout
* source file names
* Turtle serialization
* JSON-LD serialization
* GraphDB repository names
* API implementation
* programming language
* deployment environment

Stable identifiers allow independently developed software components to reference the 
same semantic resources.

---

## Decision

The project shall use HTTP IRIs rooted at:

```text
https://dynamicontology.com/uad36/
```

Every RDF resource shall be assigned a stable IRI that remains valid regardless of where 
or how the resource is stored.

The physical location of a resource shall never determine its identity.

---

## Guiding Principles

### Identity Is Permanent

An RDF resource has one identity.

Its identity shall not change because:

* the source file is renamed
* the repository structure changes
* the serialization changes
* the software implementation changes
* the GraphDB repository changes

Identity is a semantic property, not a storage property.

---

### Serialization Independence

The same resource may be represented as:

* Turtle
* RDF/XML
* JSON-LD
* N-Triples

without changing its identity.

Example:

```text
Resource Identity

https://dynamicontology.com/uad36/ontology

Possible Serializations

ontology/uad36-core.ttl

ontology/uad36-core.jsonld

ontology/uad36-core.rdf
```

These are different representations of the same resource.

---

### Repository Independence

GitHub repository layout is an implementation concern.

Examples such as:

```text
ontology/uad36-core.ttl

docs/architecture/uad-rdf-model.md
```

are repository paths.

They are not semantic identifiers.

---

## Namespace Families

The project separates ontology vocabulary from generated resources.

### Ontology Vocabulary

```text
https://dynamicontology.com/uad36/ontology#
```

Preferred prefix:

```turtle
@prefix uad: <https://dynamicontology.com/uad36/ontology#> .
```

Examples:

```text
uad:SchemaComponent
uad:ValidationRule
uad:ValidationFinding
uad:SpecificationSource
```

---

### Generated Schema Resources

```text
https://dynamicontology.com/uad36/schema#
```

Preferred prefix:

```turtle
@prefix uadschema: <https://dynamicontology.com/uad36/schema#> .
```

Examples:

```text
uadschema:PropertyAddress
uadschema:SubjectProperty
uadschema:ComparableSale
```

---

### Controlled Values

```text
https://dynamicontology.com/uad36/value#
```

Preferred prefix:

```turtle
@prefix uadvalue: <https://dynamicontology.com/uad36/value#> .
```

Examples:

```text
uadvalue:ConditionRating

uadvalue:C3

uadvalue:Q4
```

Controlled values may later be represented as SKOS concepts.

---

### Validation Rules

```text
https://dynamicontology.com/uad36/rule#
```

Preferred prefix:

```turtle
@prefix uadrule: <https://dynamicontology.com/uad36/rule#> .
```

Examples:

```text
uadrule:H-001

uadrule:H-105
```

Rule identifiers should preserve published rule identifiers whenever practical.

---

### Relationship Predicates

```text
https://dynamicontology.com/uad36/predicate#
```

Preferred prefix:

```turtle
@prefix uadpred: <https://dynamicontology.com/uad36/predicate#> .
```

Examples:

```text
uadpred:DATA_SOURCE_IsDataSourceFor_AccessoryDwellingUnitLegallyRentableIndicator

uadpred:PARTY_IsBorrowerFor_LOAN
```

Relationship predicates identify governed RDF predicates used to express graph relationships.

Predicates may be derived from XLink arcroles, Appendix A mappings, schema relationships,
or other authoritative UAD/GSE relationship definitions. The generated predicate IRI shall
not imply ownership by MISMO or the GSEs unless the source authority explicitly defines that
IRI. Source identifiers such as XLink arcrole URNs shall be preserved as provenance metadata.

---

### Source Documents

```text
https://dynamicontology.com/uad36/source#
```

Preferred prefix:

```turtle
@prefix uadsource: <https://dynamicontology.com/uad36/source#> .
```

Examples:

```text
uadsource:AppendixA

uadsource:AppendixH

uadsource:DeliverySpecification
```

---

### Appraisal Instance Resources

Generated appraisal resources are transient.

Their identities should use hierarchical paths rather than fragment identifiers.

Base namespace:

```text
https://dynamicontology.com/uad36/instance/
```

Example:

```text
https://dynamicontology.com/uad36/instance/Report123/PropertyAddress
```

---

### Validation Findings

Validation findings are generated artifacts.

Base namespace:

```text
https://dynamicontology.com/uad36/finding/
```

Example:

```text
https://dynamicontology.com/uad36/finding/Run456/Finding17
```

---

## Fragment Versus Path Identifiers

The project adopts the following convention.

Use fragment identifiers (`#`) for stable vocabulary resources.

Examples:

```text
https://dynamicontology.com/uad36/ontology#ValidationRule

https://dynamicontology.com/uad36/schema#PropertyAddress

https://dynamicontology.com/uad36/value#C3

https://dynamicontology.com/uad36/predicate#DATA_SOURCE_IsDataSourceFor_AccessoryDwellingUnitLegallyRentableIndicator
```

Use hierarchical paths (`/`) for generated resources.

Examples:

```text
https://dynamicontology.com/uad36/instance/Report123

https://dynamicontology.com/uad36/finding/Run456/Finding17
```

This convention distinguishes stable vocabulary from generated data.

---

## Relationship to ADR 0001

ADR 0001 establishes the ontology namespace.

This ADR extends that decision by defining the namespace strategy for all RDF resources 
used by the UAD 3.6 Validation project.

---

## Consequences

All generated RDF assets shall mint IRIs using this policy.

Future generators shall not derive resource identities from:

* XML paths
* local filenames
* GraphDB identifiers
* API endpoint names

Instead, generators shall produce stable IRIs that remain valid regardless of 
implementation.

---

## Future Decisions

Future Architecture Decision Records may define:

* XML ID to IRI mapping
* namespace versioning strategy
* appraisal instance identity policy
* cross-version identity management
* XLink arcrole provenance properties
* external ontology alignment

These decisions shall extend this policy rather than replace it.

---

## References

* ADR 0001: Project Namespace
* `docs/architecture/uad-rdf-model.md`
* `docs/architecture/uad36-ontology.md`
* W3C Resource Description Framework (RDF)
* W3C Web Ontology Language (OWL)
