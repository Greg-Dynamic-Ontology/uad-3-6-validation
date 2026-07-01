# URAR Meaning Model

**Status:** Draft

## Purpose

The purpose of this document is to describe the conceptual meaning of the Uniform
Residential Appraisal Report (URAR) independently of its XML representation.

The MISMO XML Schema defines the carrier used to exchange appraisal information.

The URAR Implementation Guide describes the intended interpretation and use of the 
information carried by the XML. Together with accepted appraisal practice, it provides 
the semantic foundation for this model.

The RDF model described in this document captures that meaning.

---

## Projection Families

The ontology is materialized through multiple families of representations.
Each family serves a different purpose while preserving the underlying
conceptual meaning.

```
                   More Abstract
                        ↑

 Documentation      Semantic         Constraint
     Family          Family           Family
     --------        --------         ----------
 Implementation      RDF/OWL          SHACL
 Guide               SKOS             Rules
 Glossary            Ontologies

---------------------------------------------------------

 Exchange            Persistence      Analytics
  Family              Family           Family
 ---------           -----------      ----------
 XML Schema          SQL Schema       Measurements
 JSON Schema         GraphDB          Findings
 XML Instance        RDF Instance     Reports

                        ↓
                   More Concrete
```

No family is privileged over another.

The same conceptual entity may appear in multiple families.

For example:

| Family        | Subject Property             |
|---------------|------------------------------|
| Documentation | Implementation Guide section |
| Semantic      | `uad:SubjectProperty`        |
| Constraint    | SHACL Shape                  |
| Exchange      | XML Element                  |
| Persistence   | RDF node or relational row   |
| Analytics     | Completeness measurement     |

Each representation is a projection of the same underlying ontology, optimized for a 
different purpose.

---
## Meaning

The purpose of an appraisal is to communicate a professional opinion of value.

Neither the XML Schema nor the XML instance contains that meaning directly.

Instead, meaning emerges from three complementary artifacts:

* the MISMO data model, which carries the information;
* the URAR Implementation Guide, which explains how the information is used;
* the appraisal profession, which supplies the domain knowledge necessary to interpret 
that information.

This document reconstructs the conceptual model implied by those artifacts.

The resulting RDF model is not a translation of XML.

It is a semantic representation of the appraisal itself.

---

# Appraisal

An appraisal is a professional opinion of value supported by evidence.

It is not merely a document.

The report delivered to the GSEs is one representation of that appraisal.

The ontology therefore models the appraisal itself rather than the report layout.

```turtle
uad:Appraisal
    a owl:Class ;
    rdfs:label "Appraisal" ;
    skos:definition
        "A professional opinion of value supported by documented evidence." .
```
---

# Opinion of Value

An appraisal exists to communicate an opinion of value.

An opinion of value is a professional judgment reached through the analysis of
available evidence using accepted appraisal methods.

An opinion is not a fact.

It is a reasoned conclusion that should be traceable to the supporting
observations, analyses, and evidence contained in the appraisal.

The purpose of the appraisal is therefore not merely to collect information but
to justify an opinion of value.

```turtle
uad:OpinionOfValue
    a owl:Class ;
    rdfs:label "Opinion of Value" ;
    skos:definition
        "A professional opinion regarding the value of a subject property supported by documented evidence." .
```

An appraisal produces one or more opinions of value.

```turtle
uad:hasOpinionOfValue
    a owl:ObjectProperty ;
    rdfs:domain uad:Appraisal ;
    rdfs:range uad:OpinionOfValue .
```

Evidence supports an opinion of value.

```turtle
uad:supportsOpinionOfValue
    a owl:ObjectProperty ;
    rdfs:domain uad:Evidence ;
    rdfs:range uad:OpinionOfValue .
```

An opinion of value concerns a subject property.

```turtle
uad:isOpinionOfValueFor
    a owl:ObjectProperty ;
    rdfs:domain uad:OpinionOfValue ;
    rdfs:range uad:SubjectProperty .
```
---

# Subject Property

Every appraisal concerns exactly one subject property.

The subject property is the object being analyzed.

It is described by many observations but remains a single conceptual entity.

```turtle
uad:SubjectProperty
    a owl:Class ;
    rdfs:subClassOf uad:RealProperty ;
    rdfs:label "Subject Property" .
```

The appraisal references its subject property.

```turtle
uad:appraisesProperty
    a owl:ObjectProperty ;
    rdfs:domain uad:Appraisal ;
    rdfs:range uad:SubjectProperty .
```

---

# Evidence

Evidence supports an appraisal.

Evidence may include:

* observations
* inspections
* photographs
* public records
* comparable sales
* market data

Evidence supports conclusions.

Evidence does not determine conclusions.

```turtle
uad:Evidence
    a owl:Class ;
    rdfs:label "Evidence" .
```

```turtle
uad:supportsConclusion
    a owl:ObjectProperty ;
    rdfs:domain uad:Evidence ;
    rdfs:range uad:ValuationConclusion .
```

---

# Comparable Sale

A comparable sale is not merely another property.

It is evidence used in evaluating the subject property.

The same property may serve as a comparable in multiple appraisals.

```turtle
uad:ComparableSale
    a owl:Class ;
    rdfs:subClassOf uad:Evidence .
```

```turtle
uad:usesComparableSale
    a owl:ObjectProperty ;
    rdfs:domain uad:SalesComparisonApproach ;
    rdfs:range uad:ComparableSale .
```

---

# XLink

The XML hierarchy is not enough to represent many appraisal relationships.

MISMO therefore uses XLink to express semantic relationships.

The ontology models these relationships directly.

XLink arcroles become governed RDF predicates.

```turtle
uadpred:DATA_SOURCE_IsDataSourceFor_AccessoryDwellingUnitLegallyRentableIndicator
    a owl:ObjectProperty ;
    rdfs:subPropertyOf uad:supportsObservation .
```

---

# Measurements

Measurements are computed over the semantic graph rather than directly over XML.

Examples include:

* completeness
* consistency
* provenance
* evidence coverage
* comparable distribution
* adjustment analysis
* business rule compliance

A measurement is itself a first-class semantic artifact.

```turtle
uad:MeasurementRun
    a owl:Class .

uad:Measurement
    a owl:Class .

uad:producedMeasurement
    a owl:ObjectProperty ;
    rdfs:domain uad:MeasurementRun ;
    rdfs:range uad:Measurement .
```