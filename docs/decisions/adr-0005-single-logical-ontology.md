# Architecture Decision Record 0005: Single Logical Ontology

**Status:** Accepted

**Date:** 2026-07-03

## Context

The UAD 3.6 Validation project is developing a conceptual ontology for the
Uniform Appraisal Dataset (UAD) 3.6.

As the ontology grows, it is desirable to organize the source into multiple
Turtle files to improve readability, simplify maintenance, and allow different
areas of the ontology to evolve independently.

Examples include:

- core ontology declarations;
- appraisal meaning;
- vocabulary extracted from XML Schema;
- controlled vocabularies;
- generated semantic assets;
- SHACL constraints;
- examples.

A common approach in OWL is to publish multiple ontologies connected using
`owl:imports`.

While appropriate for independently versioned ontologies, this introduces
additional complexity during early ontology development and obscures the fact
that these source files together describe a single conceptual model.

The project currently views these files as source modules that contribute to one
logical ontology rather than as independently managed ontologies.

## Decision

The UAD ontology shall be developed as a **single logical ontology**
distributed across multiple Turtle source files.

All ontology terms shall use the common namespace:

```
https://dynamicontology.com/uad36/ontology#
```

The ontology shall contain a single ontology declaration:

```
<https://dynamicontology.com/uad36/ontology>
    a owl:Ontology .
```

This ontology declaration is maintained in:

```
ontologies/uad36-core.ttl
```

Additional Turtle files contribute classes, properties, individuals, and other
ontology resources using the shared namespace.

These files intentionally do **not** declare additional `owl:Ontology`
resources.

## Source Organization

Current ontology source files include:

- `uad36-core.ttl`
- `urar-meaning.ttl`

Additional files may be added as the ontology grows.

Possible future source files include:

- `xsd-complex-types.ttl`
- `xsd-simple-types.ttl`
- `xsd-elements.ttl`
- `xsd-attributes.ttl`
- `xsd-arcroles.ttl`
- `uad-controlled-vocabularies.ttl`
- `vocabulary-alignment.ttl`
- `urar-meaning.ttl`
- `measurements.ttl`
- `validation.ttl`

MISMO source artifacts are expressed using XML Schema vocabulary, such as
complex types, simple types, elements, attributes, model groups, and XLink
arcroles. Generated RDF assets should preserve that source vocabulary rather
than prematurely recasting MISMO constructs as domain classes and properties.

A separate vocabulary-alignment layer may relate schema-derived resources to
meaning-model resources. For example, an XSD complex type may be aligned with a
UAD meaning-model class, and an XSD element may be aligned with a semantic
property or concept used in RDF projection.
These remain source files contributing to a single logical ontology.

## Rationale

A single logical ontology provides several advantages.

### Clear Identity

There is only one ontology IRI representing the UAD ontology.

Applications consuming the ontology need not determine which ontology is
authoritative.

### Simpler Development

Developers can divide the ontology into manageable source files without creating
artificial ontology boundaries.

### Consistent Namespace

Every class and property belongs to the same semantic namespace regardless of
which Turtle file contains its definition.

### Easier Testing

Regression tests can load multiple Turtle source files into a single RDF graph
and validate the ontology as a whole.

This matches how the ontology is intended to be used.

### Future Flexibility

Nothing in this decision prevents future modularization.

If portions of the ontology eventually become independently versioned or reused
outside the UAD project, separate ontology modules connected by
`owl:imports` may be introduced without changing the ontology namespace.

## Experimental Alternative

During development the project considered treating individual Turtle files as
independent ontologies.

For example:

```turtle
<https://dynamicontology.com/uad36/urar-meaning>
    a owl:Ontology ;
    owl:imports <https://dynamicontology.com/uad36/ontology> .
```

This approach has been intentionally deferred.

The project concluded that the additional complexity does not currently provide
sufficient benefit while the ontology is still evolving.

Commented examples of this alternative may remain within source files to
document the architectural decision.

## Consequences

Ontology source files should be viewed as implementation units rather than
semantic boundaries.

Moving a class or property from one Turtle file to another does not change its
meaning because the resource IRI remains unchanged.

Ontology regression tests should validate the complete logical ontology rather
than individual source files in isolation.

Documentation should describe the ontology as a single conceptual model
implemented across multiple source files.

## Alternatives Considered

### Multiple Independent Ontologies

Deferred.

Appropriate when ontology modules are independently versioned or published.

Not currently justified for UAD ontology development.

### Single Monolithic Turtle File

Rejected.

A single file becomes increasingly difficult to navigate, review, maintain, and
test as the ontology grows.

Multiple source files provide better organization without fragmenting the
conceptual ontology.

## Related ADRs

- ADR 0001 — Project Namespace
- ADR 0002 — IRI Minting Policy
- ADR 0003 — Generated Semantic Assets
- ADR 0004 — Meaning-First Ontology Development