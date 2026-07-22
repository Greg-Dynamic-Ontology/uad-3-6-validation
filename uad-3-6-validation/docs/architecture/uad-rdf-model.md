# UAD 3.6 RDF Model
## 1. Design Principles

### 1.1 Purpose

The purpose of the UAD 3.6 RDF Model is to provide a canonical semantic representation 
of the Uniform Appraisal Dataset (UAD) 3.6 specifications. The RDF model serves as the 
authoritative knowledge representation from which validation, querying, reasoning, 
reporting, and future tooling can be derived.

The RDF model is intended to complement—not replace—the published GSE specifications.

---

### 1.2 Design Goals

The model is designed to satisfy the following goals:

* Preserve the meaning of the published UAD 3.6 specifications.
* Maintain complete traceability back to the authoritative GSE source documents.
* Represent both schema structure and semantic relationships.
* Support deterministic validation.
* Support graph-based reasoning and querying.
* Support future API, GraphDB, and knowledge engineering applications.
* Remain independent of any particular software implementation.

---

### 1.3 Canonical Source Principle

The published GSE specifications remain the authoritative source.

The RDF model is a semantic representation derived from those specifications and shall 
never become the source of record.

Project assets are divided into two categories:

**Authoritative Sources**

* GSE published schemas
* GSE implementation guides
* GSE appendices
* GSE compliance rules
* GSE sample appraisal packages

**Generated Artifacts**

* RDF models
* Turtle serializations
* SHACL shapes
* GraphDB repositories
* Generated reports
* Derived documentation

Generated artifacts may always be regenerated from the authoritative sources.

---

### 1.4 RDF Before GraphDB

GraphDB is considered a deployment platform rather than the primary representation.

The canonical representation of the specification is RDF.

```
Published Specifications
        ↓
Canonical RDF Model
        ↓
Turtle Serialization
        ↓
GraphDB Repository
```

This separation allows the RDF model to remain independent of any specific graph database 
implementation.

---

### 1.5 Stable Identity

Every significant semantic resource shall possess a stable, globally unique IRI.

Examples include:

* schema components
* XML elements
* XML attributes
* datatypes
* enumerations
* controlled values
* relationship predicates
* validation rules
* validation findings

Stable IRIs allow resources to participate naturally in RDF graphs without dependence upon 
document location.

---

### 1.6 XML is a Tree; the World is Not

The UAD XML document represents information as a hierarchical tree.

Many important appraisal relationships exist independently of that hierarchy.

The RDF model captures these relationships explicitly using subject–predicate–object 
statements.

Relationships formerly expressed through XML location, identifiers, or XLink become 
explicit graph relationships using governed predicate IRIs.

---

### 1.7 Separation of Concerns

The RDF model separates distinct categories of knowledge.

These include:

* schema definitions
* controlled vocabularies
* relationship vocabularies
* validation rules
* instance data
* validation findings
* provenance

Each category may evolve independently while remaining connected through shared IRIs.

---

### 1.8 Deterministic Validation

Compliance decisions shall be based upon deterministic rules derived from the published 
specifications.

Artificial intelligence may assist with:

* explanation
* summarization
* reviewer assistance
* freeform text interpretation

Artificial intelligence shall not replace authoritative validation logic.

---

### 1.9 Provenance

Every generated semantic resource shall retain provenance information sufficient to 
identify:

* originating specification
* specification version
* appendix or section
* source location
* generation process
* generation timestamp

Every validation finding shall be traceable to the governing specification.

---

### 1.10 Extensibility

The RDF model is intended to evolve with future GSE releases without requiring redesign.

New:

* schema versions
* rule sets
* controlled vocabularies
* delivery specifications
* lender overlays

should be representable by extending the graph rather than replacing it.

---

### 1.11 Implementation Independence

The conceptual RDF model shall remain independent of:

* GraphDB
* SHACL implementation
* SPARQL implementation
* API framework
* programming language
* LLM technology

Implementation technologies may change while the semantic model remains stable.

---

### 1.12 Guiding Principle

The UAD 3.6 RDF Model represents the semantics of the UAD specifications—not merely their XML syntax.

The goal is to create a durable semantic foundation that supports validation, reasoning, interoperability, and future knowledge engineering applications while preserving complete fidelity to the published GSE specifications.

## 2. RDF Asset Layers
## 3. IRI Policy
## 4. Schema Component Model
## 5. XLink Relationship Model
## 6. Rule Model
## 7. Validation Finding Model
## 8. Provenance Model
## 9. Generated vs Source Artifacts
## 10. Open Design Questions