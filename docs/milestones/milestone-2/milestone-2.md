# Milestone 2 — Ontology Projection

## Purpose

Project a logical schema model into a semantic ontology expressed using RDF,
OWL, and SKOS.

This milestone establishes that ontology generation is based solely on the
logical schema model produced by Milestone 1 and is therefore independent of
the physical organization of the XML Schema.

---

## Inputs

- Logical Schema Model

---

## Outputs

- RDF graph
- OWL ontology
- SKOS concept schemes
- Generated ontology artifacts

---

## Transformation

```text
               Combined Schema
                     │
                     ▼
              Logical Schema Model
                     ▲
                     │
              Individual Schema

                     │
                     ▼

            ┌───────────────────┐
            │ Ontology Projector│
            └───────────────────┘
                     │
                     ▼

      RDF + OWL + SKOS Ontology Graph
```

---

## Requirements

The ontology projector shall:

1. Accept only a logical schema model as input.
2. Produce ontology artifacts that are independent of the original schema
   representation.
3. Represent structural semantics using OWL.
4. Represent controlled vocabularies using SKOS.
5. Represent graph relationships using RDF.
6. Produce deterministic ontology IRIs.
7. Preserve traceability from ontology resources back to the originating
   schema components.

---

## Projection Rules

| Logical Schema Component           | Ontology Representation |
|------------------------------------|-------------------------|
| Named simple type                  | `owl:DatatypeProperty`  |
| Named complex type                 | `owl:Class`             |
| Complex type extension             | `rdfs:subClassOf`       |
| Named simple type with enumeration | `skos:ConceptScheme`    |
| Enumeration value                  | `skos:Concept`          |
| Enumeration membership             | `skos:inScheme`         |

---

## Tests

The following conditions shall be verified.

- [ ] Every named complex type projects to one `owl:Class`.
- [ ] Every complex type extension projects to one `rdfs:subClassOf`
      relationship.
- [ ] Every named simple type projects to one `owl:DatatypeProperty`.
- [ ] Every enumerated simple type projects to one `skos:ConceptScheme`.
- [ ] Every enumeration value projects to one `skos:Concept`.
- [ ] Every concept belongs to exactly one `skos:ConceptScheme`.
- [ ] Projection is deterministic.
- [ ] Combined and Individual schemas produce equivalent ontology graphs.

---

## Completion Criteria

This milestone is complete when:

- [ ] Every projection rule has an automated test.
- [ ] All ontology projection tests pass.
- [ ] Equivalent logical schema models produce equivalent ontology graphs.
- [ ] RDF, OWL, and SKOS responsibilities are clearly separated.
- [ ] The canonical semantic representation is produced as an RDF graph. Persistence of that graph as generated ontology artifacts is controlled by Configuration Knowledge.

---

## Deliverables

### Documentation

- `docs/milestones/milestone-2-ontology-projection.md`
- `docs/architecture/xsd-to-ontology-projection.md`

### Tests

- `tests/test_xsd_to_ontology_projection.py`

### Software

- Ontology projector
- Projection rule library

### Generated Artifacts

- OWL ontology
- RDF graph
- SKOS vocabularies

---

## Knowledge Preserved

This milestone establishes the following architectural invariant.

> Every logical schema model projects to a single semantic ontology,
> independent of the physical XML Schema from which the logical schema was
> derived.

All subsequent OTDD milestones shall consume the ontology rather than the XML
Schema or the logical schema model.

---

## Notes

This milestone intentionally focuses on ontology structure rather than XML
instance data.

Instance projection, validation, and SHACL-based reasoning are deferred to
later milestones.

The purpose of this milestone is to establish a complete semantic
representation of the XML Schema using RDF, OWL, and SKOS.