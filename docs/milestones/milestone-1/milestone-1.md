# Milestone 1 — Schema Loader

**Status:** Completed

---

## Purpose

Establish a logical schema model that is independent of the physical
organization of an XML Schema.

Given either a monolithic XML Schema document or an equivalent collection of
XML Schema documents connected through `xs:include`, the schema loader shall
produce the same logical schema model.

This milestone establishes the foundation upon which every subsequent OTDD
projection depends.

---

## Motivation

XML Schemas are frequently distributed across multiple documents using
`xs:include`. Later ontology projections must not depend upon whether the
schema was authored as a single document or as multiple documents.

The purpose of this milestone is to separate the logical schema from its
physical representation.

---

## Inputs

- Combined XML Schema
- Distributed XML Schema
- Recursive `xs:include` graph

---

## Outputs

- Logical Schema Model

---

## Transformation

```text
Combined Schema
        │
        │
        ├──────────────┐
        │              │
        ▼              ▼
              Schema Loader
                    │
                    ▼
         Logical Schema Model
                    ▲
                    │
Distributed Schema
(xs:include closure)
```

---

## Requirements

- [x] Load a combined schema.
- [x] Load a distributed schema.
- [x] Resolve recursive `xs:include`.
- [x] Resolve relative include paths.
- [x] Prevent duplicate processing.
- [x] Prevent circular include recursion.
- [x] Correctly implement XML Schema chameleon namespace inheritance.
- [x] Produce a single logical schema model.

---

## Projection Rules

| Physical Schema Construct | Logical Schema Representation |
|---------------------------|-------------------------------|
| Global element            | Global element                |
| Global attribute          | Global attribute              |
| Named complex type        | Named complex type            |
| Named simple type         | Named simple type             |
| Included schema           | Merged into logical schema    |
| File boundaries           | Ignored                       |

---

## Tests Executed

| Test                            | Status |
|---------------------------------|--------|
| Combined schema loads           | ✅      |
| Distributed schema loads        | ✅      |
| Recursive include processing    | ✅      |
| Relative include resolution     | ✅      |
| Chameleon namespace inheritance | ✅      |
| Global element counts match     | ✅      |
| Global attribute counts match   | ✅      |
| Complex type counts match       | ✅      |
| Simple type counts match        | ✅      |
| Global element sets equal       | ✅      |
| Global attribute sets equal     | ✅      |
| Complex type sets equal         | ✅      |
| Simple type sets equal          | ✅      |
| Logical schema models equal     | ✅      |

---

## Deliverables

### Software

- Schema loader
- Logical schema model

### Tests

- `tests/test_logical_schema_counts.py`

### Documentation

- *(To be completed.)*

---

## Knowledge Preserved

> Given either a combined XML Schema or an equivalent distributed XML Schema,
> the schema loader shall always produce the same logical schema model.

Future milestones shall consume the logical schema model rather than the
physical XML Schema documents.

---

## Lessons Learned

- XML Schema chameleon includes required explicit namespace inheritance.
- Physical file boundaries are not part of the logical schema.
- Regression tests proved equivalence rather than implementation details.
- The logical schema model became the canonical output of schema loading.

---

## History

This milestone was implemented before the milestone documentation format was
established.

The document has been retrofitted to preserve the architectural decisions,
tests, and invariant established during implementation.