# Ontology Test-Driven Development (OTDD) Development Flow

> **Status:** Working Notes
>
> This document captures the emerging Ontology Test-Driven Development
> (OTDD) methodology as practiced during development of the UAD 3.6
> Validation project.
>
> It is intentionally iterative and will evolve as additional experience
> is gained. After completion of the UAD project this document will move
> into the dedicated OTDD project.

---

# Overview

Traditional Test-Driven Development (TDD) begins after software
requirements have been established.

Ontology Test-Driven Development (OTDD) begins earlier.

OTDD first validates the meaning of the system being built before
software testing begins.

In short,

> **The "O" precedes the "TDD".**

---

# Development Flow

```
============================
Ontology Test-Driven Development
============================
        │
        ▼
Business Meaning
(.md,.rdf,.pdf,.xlsx)
        │
        ▼
Meaning Validation
(SHACL, SKOS, Competency Questions)
        │
        ▼
    Ontology
    (.ttl)
        │
        ▼
Ontology Validation
(SHACL, Reasoning, Competency Questions)
        │
        ▼
Architecture
        │
        ▼
Architecture Validation
(Review, Characterizati Tests,
 Architectural Tests)
        │
        ▼
Architecture Decision Record
        │
        ▼
============================
Behavior-Driven Development
============================
        │
        ▼
BDD Feature
        │
        ▼
=========================
Test-Driven Development
=========================
        │
        ▼
Pytest Tests
        │
        ▼
Implementation
        │
        ▼
Executable Product
(executable, application,
 web service, product library,
 knowledge graph)
        │
        ▼
Human Evaluation
(User, Domain Expert,Developer)
        │
        └──────────────────────┐
                               │
                               ▼
                     Business Meaning
```

---

# Meaning Validation

Meaning validation confirms that the business concepts have been
correctly understood before implementation begins.

Typical activities include:

- identifying domain concepts
- defining terminology
- eliminating ambiguity
- distinguishing business concepts from implementation concepts
- validating business understanding with domain experts

Typical discoveries are semantic, not software defects.

Examples from the UAD project include:

- Configuration changes the user experience.
- Configuration does not change the validation pipeline.
- RDF Projection is a pipeline stage.
- Turtle is a developer artifact, not a user artifact.

---

# Ontology Validation

Ontology validation confirms that the conceptual model faithfully
represents the validated business meaning.

Validation techniques include:

- competency questions
- ontology review
- SHACL validation
- consistency checking
- traceability to governing specifications

---

# Architecture Validation

Architecture validation confirms that the software architecture
implements the ontology.

Examples include:

- pipeline ordering
- separation of concerns
- artifact lifecycle
- configuration model
- user experience model

---

# TDD

Once the ontology and architecture have been validated, traditional
Test-Driven Development begins.

Typical cycle:

1. Write failing test.
2. Implement smallest change.
3. Green.
4. Refactor.

OTDD does not replace TDD.

OTDD establishes the semantic foundation upon which TDD operates.

---

# Human Evaluation

Executable software remains subject to human evaluation.

During UAD development each visible iteration is reviewed by executing

```
python -m uvicorn app.main:app --reload
```

and evaluating the resulting application from the user's perspective.

Questions include:

- Is the workflow understandable?
- Is the terminology correct?
- Does the application express the intended business meaning?
- Does this iteration improve the product?

---

# Core Principle

Ontology precedes implementation.

Business meaning precedes ontology.

Validation occurs at every level.

OTDD therefore complements TDD rather than replacing it.

```
Meaning
    ↓
Ontology
    ↓
Architecture
    ↓
TDD
    ↓
Implementation
```

---

# Current Status

This document represents the current understanding of OTDD as developed
during implementation of the UAD 3.6 Validation project.

It is expected to evolve through continued application and experience.