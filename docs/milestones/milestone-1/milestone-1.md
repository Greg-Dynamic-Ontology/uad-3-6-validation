# Milestone 1 — Schema Loader

**Status:** In Progress

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

In preparation for Milestone 2, it was recognized that the Logical Schema
Model must also exist as a persistent RDF graph. This graph provides a stable,
inspectable, versionable artifact for testing, regression analysis, and
interchange.

---

## Inputs

- Combined XML Schema
- Distributed XML Schema
- Recursive `xs:include` graph

---

## Outputs

- Logical Schema Model (runtime object)
- Logical Schema Graph (RDF/Turtle serialization)

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
             │            │
             │            ▼
             │   Logical Schema Graph
             │      (RDF/Turtle)
             │
             ▼
        Runtime Consumers

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
- [ ] Serialize the Logical Schema Model as an RDF/Turtle graph.

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

## Remaining Work

| Task                                          | Status |
|-----------------------------------------------|--------|
| Serialize Logical Schema Model to RDF/Turtle  | ⬜      |
| Verify serialized graph against runtime model | ⬜      |
| Add regression tests for serialized graph     | ⬜      |

---

## Deliverables

### Software

- Schema loader
- Logical Schema Model

### Generated Artifacts

- `artifacts/logical-schema.ttl` *(pending)*

### Tests

- `tests/test_logical_schema_counts.py`
- Serialization regression tests *(pending)*

### Documentation

- `docs/milestones/milestone-1/milestone-1.md`

---

## Knowledge Preserved

> Given either a combined XML Schema or an equivalent distributed XML Schema,
> the schema loader shall always produce the same logical schema model.

Future milestones shall consume the Logical Schema Model rather than the
physical XML Schema documents.

The Logical Schema Model may be represented in memory for runtime processing
and as an RDF/Turtle graph for testing, regression verification, and
interchange.

---

## Lessons Learned

- XML Schema chameleon includes required explicit namespace inheritance.
- Physical file boundaries are not part of the logical schema.
- Regression tests proved equivalence rather than implementation details.
- The logical schema model became the canonical output of schema loading.
- A persistent RDF representation of the logical schema is required to provide
  a durable milestone artifact and the input contract for subsequent
  milestones.

---

## History

This milestone was implemented before the milestone documentation format was
established.

The document has been retrofitted to preserve the architectural decisions,
tests, and invariants established during implementation.

During planning for Milestone 2, it became clear that the Logical Schema Model
must also be persisted as an RDF/Turtle graph. This requirement has been added
to the milestone. Until the serialization artifact and its associated
regression tests are implemented, this milestone remains **In Progress**.