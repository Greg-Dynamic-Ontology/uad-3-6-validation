# Basic XSD-to-RDF Translation Profile

## Status

Draft

## Purpose

The **Basic XSD-to-RDF Translation Profile** defines the deterministic translation of
XML Schema (XSD) constructs into RDF.

The profile intentionally translates **only what the XSD explicitly states**.
It does **not** attempt to infer additional business meaning or ontology
semantics.

This profile is the first reference implementation of the OTDD principle:

> Knowledge transformations are themselves knowledge.

Instead of embedding translation decisions in Python, the translation rules are
represented as RDF in a TriG document. The translation engine interprets those
rules.

---

## Design Goals

The profile has five primary goals.

1. Make every translation decision explicit.
2. Represent translation knowledge as RDF.
3. Separate schema structure from business meaning.
4. Allow translation rules to be versioned and tested.
5. Keep the translation engine independent of individual translation profiles.

---

## Scope

This profile translates XML Schema constructs into RDF representations.

It does **not** attempt to infer:

- business meaning
- domain semantics
- ontology design
- validation rules beyond those explicitly represented by the schema

Those are addressed by later OTDD artifacts such as:

- meaning ontologies
- SHACL validation profiles
- business rule ontologies

---

## Translation Philosophy

This profile follows a conservative translation strategy.

It represents:

- what the XSD explicitly declares
- no more
- no less

For example,

```
<xsd:complexType>
```

is translated to an OWL class because a complex type represents a reusable
structured concept.

Conversely,

```
<xsd:extension>
```

is **not** translated directly into

```
rdfs:subClassOf
```

because XML Schema extension is a structural mechanism rather than a guaranteed
semantic specialization.

Instead the profile records the XSD derivation explicitly.

---

## Why TriG?

Translation rules are stored in a TriG document rather than Turtle.

TriG supports named graphs.

Named graphs allow the profile to distinguish between:

- profile metadata
- vocabulary definitions
- translation rules

while remaining a single RDF dataset.

---

## Dataset Structure

The current profile contains named graphs for:

- Profile metadata
- Translation vocabulary
- Translation rules

Additional graphs may be introduced in later versions for:

- examples
- test cases
- deprecated rules
- profile history

---

## Translation Engine

The Python translation engine is intentionally simple.

Its responsibilities are limited to:

1. Parse the XML Schema.
2. Identify the current XSD construct.
3. Locate the corresponding translation rule.
4. Execute the translation.
5. Emit RDF.

The engine does **not** decide how individual XSD constructs should be
translated.

Those decisions belong to the translation profile.

---

## Context Sensitive Translation

Some XSD constructs require additional context before the final RDF
representation can be determined.

For example,

```
xsd:element
```

initially translates to

```
rdf:Property
```

After the referenced or inline XSD type has been examined, the translator may
refine that property into either

- owl:ObjectProperty

or

- owl:DatatypeProperty

The translation profile therefore records the initial mapping while allowing the
translator to perform deterministic refinement.

---

## Relationship to OTDD

This translation profile demonstrates an important OTDD principle.

Traditional software embeds translation logic inside procedural code.

OTDD represents the translation itself as knowledge.

The translation profile therefore becomes:

- reviewable
- version controlled
- testable
- reusable
- independently evolvable

without modifying the translation engine.

---

## Testing

The translation profile will be developed using Ontology Test-Driven
Development.

Each translation rule should eventually have one or more executable tests.

Typical tests include:

- Given an XSD construct
- Apply the Basic XSD-to-RDF profile
- Verify the generated RDF

The profile itself therefore becomes the primary artifact under development.

___
## The Plan 

There are **two mappings**.

### Level 1 — Schema Mapping

This is a static mapping.

```
UAD XSD
    ↓
RDF Schema
```

This produces the RDF schema (ontology and vocabulary) that defines the RDF representation of a
UAD instance.

For example:

* Complex types → RDF classes
* Elements → RDF properties
* Datatypes → RDF datatypes
* Enumerations → controlled vocabulary

This mapping is done **once per version of the XSD**.

---

### Level 2 — Instance Mapping

This is dynamic.

```
Valid XML Instance
        │
        │ conforms to
        ▼
      UAD XSD
        │
        ▼
RDF Instance Graph
        │
        │ conforms to
        ▼
    RDF Schema
```

The instance translator is semantics-preserving. It materializes an RDF instance that conforms to the RDF schema 
derived from the XSD. It introduces no additional business semantics.

It simply materializes an RDF instance that is valid with respect to the RDF schema created in 
Level 1.

That is a much cleaner way to describe it.

---

### TriG

The target is **RDF**.

The target representation is RDF. 
When the RDF schema is expressed as a dataset of named graphs, the natural serialization 
is TriG. 
In that case, RDF instances are likewise serialized as TriG datasets so that they conform to 
the same graph organization.

So the architecture becomes:

```
            UAD XSD
               │
               ▼
          RDF Schema
               ▲
               │
Valid XML ─────────────► RDF Instance
 Instance                 Graph
```

If a single graph is sufficient:

```
RDF
```

If multiple graphs are needed:

```
TriG
```

TriG is therefore **a serialization choice**, not a semantic layer.

---

### Validation

That leads naturally to:

```
UAD XML
      │
      ▼
XSD Validation
      │
      ▼
Instance Mapping
      │
      ▼
RDF Instance
      │
      ├── SHACL
      ├── SPARQL
      └── Measurements
```

Notice something interesting.

Neither SHACL nor SPARQL actually care whether the dataset is serialized as Turtle, TriG, 
N-Quads, or loaded directly into GraphDB.

They operate on the RDF dataset.

TriG is simply the preferred interchange syntax when the dataset contains multiple named graphs.


---

Better organization for the project:

1. **Schema Projection** — UAD XSD → RDF Schema.
2. **Instance Projection** — XML Instance → RDF Instance.
3. **Validation** — SHACL shapes and SPARQL queries evaluated against the RDF 
instance dataset.
4. **Reporting** — Human-readable results.

That decomposition feels both simpler and more rigorous than the one we were converging on 
yesterday. 
It also cleanly separates what is version-specific (the UAD schema projection) from what is 
per-document (the instance projection) and from what is policy (the validation rules).

### The validity relationship is preserved across projections.

```text
XML Instance
      │
valid with respect to
      ▼
UAD XSD

        ⇓  Projection

RDF Instance
      │
valid with respect to
      ▼
RDF Schema
```

>Projection preserves represented knowledge while changing representation.
> 
> Knowledge transformations are themselves knowledge.
---

## Future Profiles

The Basic XSD-to-RDF Translation Profile intentionally provides only the first
projection from XML Schema into RDF.

Future translation profiles may extend this work, including:

- Semantic XSD-to-OWL Translation
- XSD-to-SHACL Translation
- XML Instance-to-RDF Translation
- UAD Meaning Projection
- FHIR Meaning Projection

Each profile represents a different projection of the same underlying knowledge.

---

# Relationship to Projection

Within OTDD, every representation is viewed as a projection of an underlying
body of knowledge.

The Basic XSD-to-RDF Translation Profile defines one such projection.

It is intentionally limited to representing the structure explicitly contained
within the XML Schema.

Subsequent projections may enrich that representation with business meaning,
validation rules, or domain-specific semantics while remaining traceable to the
original schema.

---

# Summary

The Basic XSD-to-RDF Translation Profile is the first declarative translation
profile developed using OTDD.

Its purpose is not simply to translate XML Schema into RDF.

Its purpose is to demonstrate that **knowledge transformations are themselves
knowledge** and therefore deserve to be represented, versioned, reviewed, and
tested as first-class knowledge artifacts.