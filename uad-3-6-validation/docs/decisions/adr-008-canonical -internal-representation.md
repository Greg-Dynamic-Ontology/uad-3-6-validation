
# ADR 0008 – Canonical Internal Representation

**Status:** Accepted

## Context

The UAD 3.6 Validation project accepts information from multiple external representations, 
including XML instance documents, XML Schemas, implementation guides, and other structured 
artifacts.

Likewise, the project produces multiple external representations, including HTML reports, RDF 
serializations, JSON APIs, measurements, and diagnostic output.

Without a canonical internal representation, each consumer would independently interpret its 
input, leading to duplicated logic, inconsistent behavior, and increasing maintenance cost.

The project requires a single authoritative representation from which all meaningful outputs 
are derived.

---

## Decision

The canonical internal representation of the UAD 3.6 Validation system SHALL be an RDF+/OWL 
knowledge representation.

All externally meaningful information entering the system SHALL be transformed into this 
canonical representation before semantic processing.

All meaningful outputs SHALL be derived from this canonical representation.

Intermediate engineering representations MAY exist to support parsing, validation, optimization, 
or implementation, but SHALL NOT become authoritative sources of meaning.

---

## Rationale

The architecture separates engineering convenience from semantic authority.

Engineering components frequently require temporary representations, including:

* XML parser trees
* Python objects
* schema validation events
* lexical token streams
* caches
* indexes

These representations exist solely to perform computation.

The canonical RDF+/OWL representation is the only authoritative semantic representation within 
the system.

This architecture ensures:

* one semantic interpretation
* one location for reasoning
* one location for inference
* one location for measurement
* one location for validation

All user-visible outputs become projections of the canonical representation.

---

## Consequences

### Advantages

* Eliminates duplicated semantic logic.
* Enables SHACL validation over a single graph.
* Supports multiple output projections (HTML, RDF, JSON, PDF, SPARQL) from one source.
* Simplifies testing because semantic behavior is verified once.
* Enables future reasoning and inference without changing external interfaces.

### Tradeoffs

* Requires every supported input representation to be projected into RDF+/OWL.
* Introduces an explicit transformation layer between parsing and presentation.
* Some engineering components will require temporary representations before canonicalization.

---

## Architectural Pattern

```
External Representation
        │
        ▼
Parsing / Validation
        │
        ▼
Intermediate Engineering Representations
        │
        ▼
Canonical RDF+/OWL Representation
        │
        ├── SHACL Validation
        ├── Measurements
        ├── Inference
        ├── Business Rules
        ├── Analytics
        │
        ▼
Output Projections
        ├── HTML
        ├── JSON
        ├── RDF Serializations
        ├── PDF
        └── Other Formats
```

---
## Architectural Principle

Engineering components compute with intermediate representations; the system reasons over the 
canonical RDF+/OWL representation.

Intermediate representations exist to support implementation. They are not authoritative 
sources of meaning. Semantic reasoning, validation, measurement, and all externally meaningful 
projections are derived from the canonical RDF+/OWL representation.

## Notes

The existence of an intermediate representation does **not** imply semantic authority.

Semantic authority belongs exclusively to the canonical RDF+/OWL representation.

This distinction preserves a single source of truth while allowing implementation flexibility.

---

