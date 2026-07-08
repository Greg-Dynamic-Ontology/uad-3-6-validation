# Architecture Decision Record 0001: Project Namespace

**Status:** Accepted

**Date:** 2026-06-26

## Context

The UAD 3.6 Validation project represents GSE specifications as RDF resources. Every 
RDF resource requires a stable IRI that uniquely identifies the resource independently 
of any implementation technology.

The project will produce RDF assets describing:

* UAD schema components
* XML elements and attributes
* datatypes
* controlled vocabularies
* relationship predicates
* validation rules
* validation findings
* generated appraisal instance graphs
* provenance information

A single, stable namespace is required to ensure consistency across all generated RDF 
assets.

The namespace must be independent of:

* GraphDB
* FastAPI
* Python
* OTK implementation details
* future storage technologies

The namespace is an architectural decision rather than an implementation detail.

---

## Decision

The project namespace shall be:

```text
https://dynamicontology.com/uad36/ontology#
```

The preferred Turtle prefix shall be:

```turtle
@prefix uad: <https://dynamicontology.com/uad36/ontology#> .
```

The ontology resource itself shall identify this namespace as its canonical identifier.

---

## Scope

This namespace is reserved for the ontology vocabulary itself.

Examples include:

```text
uad:SchemaComponent
uad:Element
uad:Attribute
uad:ValidationRule
uad:ValidationFinding
uad:SpecificationSource
uad:hasSource
uad:appliesTo
uad:triggeredByRule
```

These resources define the semantic vocabulary used throughout the project.

---

## Future Namespaces

Additional namespaces may be introduced for generated resources.

Possible examples include:

```text
https://dynamicontology.com/uad36/schema#
https://dynamicontology.com/uad36/value#
https://dynamicontology.com/uad36/rule#
https://dynamicontology.com/uad36/report#
https://dynamicontology.com/uad36/finding#
```

These namespaces are intentionally deferred until their corresponding models have been 
designed.

This ADR governs only the ontology namespace.

---

## Rationale

Separating the ontology namespace from generated instance namespaces provides several 
benefits.

* The ontology remains stable as generated resources evolve.
* Schema resources, rules, and instance data can evolve independently.
* Different generated datasets can coexist without changing the ontology.
* Future versions of the UAD specification can reuse or extend the ontology while maintaining backward compatibility.

This approach follows established RDF and OWL practices of separating vocabulary 
definitions from instance data.

---

## Consequences

All manually authored ontology resources shall use the `uad:` prefix defined by this ADR.

Future Architecture Decision Records will define additional namespaces for:

* generated schema resources
* generated validation rules
* generated controlled vocabularies
* appraisal instance graphs
* validation findings

No implementation shall introduce an alternative ontology namespace without superseding 
this ADR.

---

## References

* `docs/architecture/uad-rdf-model.md`
* `docs/architecture/uad36-ontology.md`
* W3C Resource Description Framework (RDF)
* W3C Web Ontology Language (OWL)
