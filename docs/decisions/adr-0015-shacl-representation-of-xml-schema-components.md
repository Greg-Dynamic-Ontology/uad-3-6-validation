# ADR-0015 — SHACL Representation of XML Schema Components

**Status:** Draft

## Context

ADR-0014 defines how selected XML Schema (XSD) constructs are represented in RDF to support 
projection of UAD 3.6 XML instance documents into a canonical RDF graph.

This ADR defines how XML Schema constructs are represented as **structural SHACL constraints**.

The purpose of these SHACL shapes is to validate that an RDF graph faithfully represents an 
XML instance that conforms to the UAD 3.6 XML Schema.

These shapes are **not** intended to express Fannie Mae or Freddie Mac business rules. 
Those rules are addressed separately.

---
## Design Principle

### Structural SHACL answers the question:

> *"Could this RDF graph have been produced from a valid UAD 3.6 XML instance?"*

 It does **not** answer:

> *"Does this appraisal satisfy GSE business requirements?"*

Those questions are intentionally addressed by separate SHACL vocabularies.

---
## Decision

Only XML Schema constructs that express structural constraints are projected into SHACL.

Schema constructs that exist solely to organize XML syntax or guide projection do not produce 
SHACL constraints.

---

## XML Schema to SHACL Mapping

| XSD component  | Notes                                 | SHACL representation                                                                       |
|----------------|---------------------------------------|--------------------------------------------------------------------------------------------|
| annotation     | Documentation container.              | Optional `sh:description` or ignored.                                                      |
| any            | Not used by the UAD projection.       | Ignore.                                                                                    |
| anyAttribute   | Not used by the UAD projection.       | Ignore.                                                                                    |
| attribute      | Literal-valued property.              | `sh:property` with datatype and cardinality constraints.                                   |
| attributeGroup | Collection of attributes.             | Inline each referenced attribute constraint.                                               |
| choice         | Alternative content model.            | `sh:or` over the permitted alternative property shapes.                                    |
| complexType    | Named structured type.                | `sh:NodeShape`.                                                                            |
| documentation  | Human-readable documentation.         | `sh:description`.                                                                          |
| element        | Depends on declaration and usage.     | See Elements table below.                                                                  |
| enumeration    | Controlled vocabulary.                | `sh:in` or equivalent concept validation.                                                  |
| extension      | Base type with additional content.    | Inherit constraints from the base type and add new constraints.                            |
| fractionDigits | Numeric facet.                        | Numeric precision constraint (custom SHACL/SPARQL if required (implementation dependent)). |
| import         | External schema, different namespace. | Resolve imported schema components before generating SHACL.                                |
| include        | External schema, same namespace.      | Resolve included schema components before generating SHACL                                 |
| maxInclusive   | Numeric facet.                        | `sh:maxInclusive`.                                                                         |
| maxLength      | String facet.                         | `sh:maxLength`.                                                                            |
| minInclusive   | Numeric facet.                        | `sh:minInclusive`.                                                                         |
| pattern        | Regular expression facet.             | `sh:pattern`.                                                                              |
| restriction    | Datatype restriction.                 | Generate corresponding SHACL constraints.                                                  |
| sequence       | Ordered content model.                | No SHACL representation. Order carries no UAD business semantics.                          |
| simpleContent  | Literal content.                      | Datatype constraint on the property value.                                                 |
| simpleType     | Scalar datatype or enumeration.       | Datatype constraint or enumeration constraint.                                             |
| union          | Alternative datatypes.                | Generate `sh:or` over the member datatype constraints.                                     |

---

## Elements Table

| Element case                    | SHACL representation                                              |
| ------------------------------- | ----------------------------------------------------------------- |
| Element typed by a complex type | `sh:node` referencing the corresponding `sh:NodeShape`.           |
| Element typed by a simple type  | Datatype constraint on the property.                              |
| Element using `ref`             | Resolve the referenced declaration before generating constraints. |
| Repeating element               | `sh:minCount` / `sh:maxCount` from `minOccurs` / `maxOccurs`.     |
| Root element                    | Root `sh:NodeShape` for validating the projected RDF graph.       |

---

## Discussion

This ADR intentionally limits itself to **structural validation** derived directly from XML Schema.

Examples include:

* datatype validation
* cardinality
* string length
* numeric ranges
* regular-expression patterns
* enumerated values

These constraints determine whether an RDF graph is a faithful projection of a UAD XML instance.

Business rules defined by the Government-Sponsored Enterprises (GSEs), such as conditional requirements, reconciliation logic, cross-field dependencies, and appraisal policy, are intentionally excluded.

---

## Consequences

The implementation is divided into three independent layers:

1. **XML Schema → RDF Projection**

   * Produces ontology artifacts and projection rules.
   * Defined by ADR-0014.

2. **XML Schema → Structural SHACL**

   * Produces structural validation shapes derived from the XML Schema.
   * Defined by this ADR.

3. **GSE Business Rules → SHACL**

   * Produces business-rule validation independent of XML Schema structure.
   * Defined in a future ADR. 

The generator shall support both the Combined and Individual UAD schema distributions. 
Generated structural SHACL graphs shall be semantically equivalent regardless of which 
distribution is used as input.

This separation keeps schema-derived validation independent of appraisal policy, simplifies implementation, and allows structural conformance and business-rule conformance to evolve independently.

---
