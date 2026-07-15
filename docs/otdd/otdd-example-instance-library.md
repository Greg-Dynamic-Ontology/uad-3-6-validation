# OTDD Example Instance Library

## Purpose

Ontology Test-Driven Development (OTDD) uses a library of RDF instance documents to
demonstrate and validate ontology behavior.

Each example instance document has a single, well-defined purpose. Collectively,
the examples document the expected behavior of the ontology and provide regression
tests as the ontology evolves.

The examples are intentionally organized as named scenarios rather than sequential
versions. Their purpose is to describe semantic competency, not development history.

---

## Directory Structure

```
examples/
    valid/
        minimal-valid-appraisal.ttl
        full-valid-appraisal.ttl

    invalid/
        ...
```

The **valid** directory contains RDF instance documents that SHALL successfully
validate against the current ontology and SHACL shapes.

The **invalid** directory contains RDF instance documents that SHALL fail
validation for one specific reason.

---

## Valid Example Philosophy

Two categories of valid examples are maintained.

### Minimal Valid Example

The minimal valid example contains only the RDF expressions required to satisfy
the current competency being tested.

Its purpose is to provide the smallest graph that satisfies the ontology and
SHACL constraints.

Example:

```
minimal-valid-appraisal.ttl
```

### Full Valid Example

The full valid example represents a complete appraisal instance.

Every resource is explicitly typed.

The semantic chain of evidence is explicit.

For every resource

```
S rdf:type Ti
```

every required relationship

```
S P O
```

is present, and every object resource is explicitly typed

```
O rdf:type Tl
```

The resulting graph is completely self-describing and does not depend upon
inference to determine resource types.

---

## Invalid Example Philosophy

Every invalid example demonstrates exactly one semantic error.

Only one aspect of the graph should be intentionally incorrect.

This makes the expected validation failure obvious.

Invalid examples are classified according to which part of an RDF triple
contains the defect.

```
Subject
Predicate
Object
```

---

## Subject Errors (S)

Subject errors concern the identity or type of the subject resource.

Examples:

```
s-missing-appraisal-type.ttl

s-wrong-appraisal-type.ttl
```

Typical failures include

- missing rdf:type
- incorrect rdf:type
- unexpected resource class

---

## Predicate Errors (P)

Predicate errors concern the relationship itself.

Examples:

```
p-missing-opinion-of-value.ttl

p-missing-reconciliation.ttl

p-wrong-appraises-property.ttl

p-cardinality-multiple-subject-properties.ttl
```

Typical failures include

- missing required property
- incorrect predicate
- cardinality violations
- illegal relationship

---

## Object Errors (O)

Object errors concern the resource referenced by the predicate.

Object errors are classified according to the semantic defect rather than simply
the SHACL constraint that detects the defect.

### Object Absent

The predicate references an object resource that has no describing triples in
the RDF graph.

Example:

```
o-absent-opinion-of-value.ttl
```

### Object Untyped

The object resource exists but has no rdf:type declaration.

Example:

```
o-untyped-opinion-of-value.ttl
```

### Wrong Object Type

The object resource exists but has an incorrect rdf:type.

Examples:

```
o-wrong-type-opinion-of-value.ttl

o-wrong-type-reconciliation.ttl

o-wrong-type-subject-property.ttl
```

### Wrong Object Reference

A correctly typed resource of the expected class exists in the graph, but the
predicate references a different resource.

Examples:

```
o-wrong-reference-opinion-of-value.ttl

o-wrong-reference-reconciliation.ttl

o-wrong-reference-valuation-approach.ttl
```

The distinction between these cases is intentional.

Although several of these examples may violate the same SHACL constraint, they
represent different semantic defects that can occur in production RDF.

OTDD treats each distinct semantic defect as a separate competency example.

---

## Naming Convention

The filename identifies both the RDF component containing the defect and the
semantic nature of the defect.

### Subject

```
s-missing-type-appraisal.ttl

s-wrong-type-appraisal.ttl
```

### Predicate

```
p-missing-opinion-of-value.ttl

p-wrong-opinion-of-value-predicate.ttl

p-cardinality-multiple-opinions-of-value.ttl
```

### Object

```
o-absent-opinion-of-value.ttl

o-untyped-opinion-of-value.ttl

o-wrong-type-opinion-of-value.ttl

o-wrong-reference-opinion-of-value.ttl
```

This convention allows a developer to determine the intent of a test without
opening the file.

The naming convention also serves as a coverage plan.

As new ontology competencies are introduced, additional examples are added until
the Subject, Predicate, and Object failure modes have been adequately exercised.

The goal is not merely SHACL coverage, but semantic coverage.

---

## Test Expectations

All examples under

```
examples/valid/
```

shall successfully validate.

All examples under

```
examples/invalid/
```

shall fail validation.

Each failed validation produces a SHACL report documenting the reason for failure.

---

## Relationship to OTDD

The example instance library is a core artifact of Ontology Test-Driven Development.

Rather than treating examples as disposable test data, OTDD treats them as
persistent semantic assets.

The examples serve simultaneously as

- executable regression tests,
- ontology documentation,
- competency examples,
- implementation guidance, and
- evidence supporting the development methodology.

As the ontology grows, the example library grows with it, providing a permanent,
executable specification of expected semantic behavior.
---
## File Header Block
```turtle
# ---------------------------------------------------------------------------
# OTDD Example
# ---------------------------------------------------------------------------
# Case ID:
#
# Expected Result:
#
# RDF Component:
#
# Defect Category:
#
# Target Concept:
#
# Shape Under Test:
#
# Constraint Under Test:
#
# Expected SHACL Result:
#
# Purpose:
#
# Related Examples:
#
# Notes:
# ---------------------------------------------------------------------------
```
