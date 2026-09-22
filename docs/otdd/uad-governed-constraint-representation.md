# Selecting a Governed Constraint Representation for UAD 3.6

## Purpose

This document applies the selection process in
governed-constraint-representation-options.md to the UAD 3.6 validation project.

The objective is to choose a representation strategy for governed validation
constraints before implementing those constraints as SHACL.

This is a project decision, not a universal OTDD rule.

## Source material

The first constraint being exercised is 0100.0007 / UAD1001 from the 
Fannie Mae UAD compliance-rules spreadsheet.

The row contains governed information including:
- source constraint identifier 0100.0007;
- rule identifier UAD1001;
- data point AddressLineText;
- requirement wording;
- violation condition;
- Fatal severity;
- business context;
- source path/XPath information; and
- workbook provenance.

The workbook is fundamentally tabular. 
The row and column structure is therefore part of the governed source evidence.

The UAD project also already contains a Logical Schema RDF graph generated
from the UAD 3.6 XSD. 
That graph supplies stable schema identities and structural relationships that
the normalized constraint must reference rather than duplicate.

## Knowledge that must survive normalization

The selected representation must preserve or make explicit:
1. identity of the governed source artifact;
2. identity of the source row or constraint;
3. original source values;
4. mapping between source columns and their meanings;
5. governed rule identity;
6. requirement statement;
7. applicability context;
8. violation condition;
9. severity;
10. traceability to the source workbook;
11. links to the UAD Logical Schema resources used by the constraint; and
12. independence from the eventual SHACL implementation.

Excel formatting, colors, charts, and other workbook presentation features
are not currently known to carry governing constraint meaning and therefore
are not requirements of the normalized representation.

## Candidate evaluation

### CSVW

Fit: 
Strong for the governed source boundary.

The Fannie Mae constraint source is a spreadsheet whose relevant content is
tabular. 
CSVW explicitly models tabular data, including spreadsheets as a source form,
and preserves rows, columns, cells, datatypes, and annotations.

CSVW therefore provides a standards-based way to represent what was actually
received before project-specific semantic interpretation occurs.

Decision:

Select CSVW for the tabular source representation.

CSVW is not sufficient by itself for normalized UAD constraint semantics.
Terms such as applicability, violation condition, governed severity, and
relationship to Logical Schema resources require additional semantics.

### PROV-O

Fit: 
Strong for provenance.

OTDD requires an auditable chain from source evidence through normalization
and implementation. 
PROV-O can represent that the normalized constraint was derived from a
particular governed source entity by a particular transformation activity.

Decision: 
Select PROV-O for provenance and derivation relationships where provenance
is material to the representation.

### DCAT

Fit: 
Useful but at a different level.

DCAT can describe the Fannie Mae workbook or constraint collection as a
dataset and the XLSX file as a distribution. 
This becomes valuable if the project maintains multiple source versions,
issuers, downloads, or publication packages.

It does not solve row-level constraint semantics.

Decision: Do not make DCAT part of the minimum UAD1001 implementation. 
Retain it as a toolbox option for dataset-level governance and future source
cataloging.

### RDF Data Cube

Fit: 
Weak for the current source.

The UAD constraint workbook is tabular but is not fundamentally a
multidimensional observation dataset.
Modeling each constraint as an observation would add machinery without
clarifying the governed requirement.

Decision: Do not select Data Cube for UAD constraint normalization.

This does not reject Data Cube from the wider data-to-knowledge toolbox.

### SKOS

Fit: Potentially useful for controlled vocabularies.

UAD severities, classifications, enumerations, and similar governed term sets
may benefit from SKOS representation, particularly where labels, mappings, or
concept schemes matter.

For the first constraint, SKOS is not required merely to state that the
governed source severity is Fatal.

Decision: Retain SKOS as an optional supporting vocabulary.
Introduce it when a governed concept scheme provides clear value.

### PROF

Fit: Potentially useful for packaging.

A future UAD validation profile may consist of Logical Schema resources,
constraint requirement graphs, SHACL shapes, documentation, and term lists. 
PROF is designed to relate such resources to a profile of a specification.

Its current Working Draft status makes it inappropriate to treat as a
required foundation for the first constraint.

Decision: Retain PROF as a candidate for later packaging and publication of validation profiles.

### SHACL

Fit: Strong for executable validation, intentionally late in the process.

SHACL is the selected executable validation representation for RDF instance
graphs.

It is not selected as the sole Governed Constraint Representation because
doing so would collapse governed source evidence, normalized requirement
semantics, and executable implementation into one artifact.

Decision: Select SHACL as the executable constraint representation produced
after normalization and behavioral proof.

### Project-defined constraint vocabulary

Fit: Necessary for the semantic gap.

CSVW can preserve the source table and PROV-O can preserve derivation, 
but neither supplies all normalized concepts required by OTDD.

The UAD project therefore requires a small RDF vocabulary for normalized
constraint semantics. 
It should define only concepts not already supplied appropriately by existing
standards.

Candidate concepts include:
- GovernedConstraint;
- source constraint identifier;
- governed rule identifier;
- requirement statement;
- applicability;
- violation condition;
- governed severity;
- relationship to Logical Schema resources;
- relationship to source evidence; and
- relationship to executable SHACL implementation.

The vocabulary should remain as domain-independent as practical. 
UAD-specific terms should be represented as instances or extensions rather
than baked into generic OTDD concepts.

Decision: Select a small project-governed RDF vocabulary for normalized
constraint semantics.

Its exact vocabulary is a subsequent OTDD design task and should be developed
through Features, Rules, tests, and explicit identity policy rather than
improvised while writing UAD1001.

## Selected UAD representation strategy

For UAD 3.6, the Governed Constraint Representation will be a composed RDF
representation rather than a single vocabulary.

The initial architecture is:
```

Governed XLSX source
        |
        v
CSVW tabular representation
        |
        +---- PROV-O provenance and derivation
        |
        v
Normalized governed constraint RDF
        |
        +---- project constraint vocabulary
        |
        +---- links to UAD Logical Schema RDF
        |
        v
Behavioral specification and RDF fixtures
        |
        v
SHACL executable representation
```

Supporting standards such as DCAT, SKOS, and PROF may be added when their
specific roles are required.

####  Why this selection was made

The selection follows the source rather than forcing the source into the final
validation technology.

The source is tabular, so CSVW preserves its intrinsic structure.

OTDD requires traceability, so PROV-O supplies provenance semantics.

The normalized requirement contains constraint concepts not fully modeled
by either standard, so a minimal project vocabulary fills only that gap.

UAD already has a Logical Schema RDF representation, so normalized 
constraints link to that graph instead of creating a parallel schema
vocabulary.

SHACL remains the executable validation representation near the end of the
process.

This approach preserves the OTDD separation:

> source evidence -> normalized knowledge -> behavioral proof -> executable representation

## Consequences

The UAD project should next define and test the minimal normalized constraint
vocabulary required to represent UAD1001.

The first implementation should resist modeling every possible future
constraint concept. UAD1001 should establish the smallest useful vocabulary,
and later constraints should extend it only when governed requirements
demonstrate the need.

The representation should remain testable without requiring GraphDB at runtime. 
GraphDB and SPARQL may continue to be used as engineering tools for discovery
and verification.

## References

R1. W3C, Model for Tabular Data and Metadata on the Web: https://www.w3.org/TR/tabular-data-model/

R2. W3C, Metadata Vocabulary for Tabular Data: https://www.w3.org/TR/tabular-metadata/

R3. W3C, PROV-O: The PROV Ontology: https://www.w3.org/TR/prov-o/

R4. W3C, Data Catalog Vocabulary (DCAT) - Version 3: https://www.w3.org/TR/vocab-dcat-3/

R5. W3C, The RDF Data Cube Vocabulary: https://www.w3.org/TR/vocab-data-cube/

R6. W3C, SKOS Simple Knowledge Organization System Reference: https://www.w3.org/TR/skos-reference/

R7. W3C, Shapes Constraint Language (SHACL): https://www.w3.org/TR/shacl/

R8. W3C, The Profiles V