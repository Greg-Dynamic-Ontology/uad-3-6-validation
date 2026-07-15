# What is a Semantic Competency?

## Purpose

Software engineering has long used requirements and capabilities to
describe the behavior expected of software systems. 
Requirements define what the system shall do. 
Capabilities describe what the completed system is able to accomplish. Software is verified by
demonstrating that it satisfies those requirements.

Semantic engineering requires similar concepts and disciplines.

Ontology Test-Driven Development (OTDD) introduces the concept of the
**semantic competency** as the fundamental unit of semantic engineering.

## Requirements and Competencies

A software requirement describes a business or technical objective.

One requirement may require multiple semantic competencies.

For example:

**Requirement**

> The semantic model shall represent the condition of the subject
> property.

One semantic competency derived from that requirement might be:

**Semantic Competency**

> Every `SubjectProperty` shall have exactly one
> `PropertyConditionRating`.

This competency is sufficiently precise that it can be independently
implemented, verified, and traced.

## Definition

A **semantic competency** is the smallest independently testable unit
of semantic behavior that can be traced from a requirement through
executable examples to the ontology and its validation artifacts.

Three characteristics distinguish a semantic competency.

- It is independently understandable.
- It is independently testable.
- It is independently traceable.

If a competency cannot be independently verified, it should probably be
decomposed into smaller semantic competencies.

## The Primary Engineering Object

OTDD treats semantic competencies as the primary engineering objects.

Other project artifacts exist to implement, verify, and document those
competencies.

Typical artifacts associated with a semantic competency include:

- Business or technical requirement
- RDF example library
- Executable verification
- SHACL shapes
- Ontology classes and properties
- Architecture Decision Records (ADRs)
- Project documentation

Rather than viewing ontologies, SHACL, examples, and tests as
independent deliverables, OTDD views them as coordinated projections of
one or more semantic competencies.

## Traceability

Every production semantic artifact should be traceable to one or more
semantic competencies.

Likewise, every semantic competency should identify the artifacts that
implement and verify it.

This traceability provides confidence that every ontology class,
property, SHACL shape, example, and executable test exists for an
explicit engineering reason.

## Looking Forward

As OTDD matures, semantic competencies may become first-class project
artifacts.

Tooling such as OTK may eventually manage semantic competencies
directly, generating and maintaining the associated examples,
verification, ontology artifacts, documentation, and traceability
relationships automatically.

The semantic competency therefore becomes not only the conceptual
foundation of OTDD, but also the organizing principle of the semantic
development shop.