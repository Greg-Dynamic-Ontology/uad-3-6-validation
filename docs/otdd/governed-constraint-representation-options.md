# Governed Constraint Representation Options

## Purpose

This document surveys representation options that may be used when converting
governed source material into a Governed Constraint Representation for OTDD.

A Governed Constraint Representation is the project representation of a
normalized constraint requirement that preserves governed identity, meaning,
applicability, severity, and provenance independently of any executable
validation representation such as SHACL.

The purpose of this document is not to select one universal representation. 
Different source structures and project goals may require different standards,
vocabularies, or combinations of standards.

## Selection process

Before selecting a representation, describe the source artifact and the
knowledge that must survive transformation.

For each candidate representation, ask:

- What is the intrinsic structure of the source data? 
- What source identities must remain stable?
- What semantics must survive projection?
- What provenance must remain traceable?
- What information is presentation-only and may be discarded?
- What is the candidate standard intended to represent?
- Is the candidate mature, governed, and interoperable?
- Does it support or map naturally into RDF when graph representation is
required?
- Can it coexist with other standards and domain vocabularies?
- Can the transformation into the representation be tested deterministically?
- Does the representation remain independent of the executable validation
technology?

A selection should be derived from these questions rather than from familiarity
with a particular technology.

## Structural starting point

From a mathematical perspective, source data may commonly appear as specialized
structures within a broader graph-representable space. 
Examples include sequences, trees, tables, and tensors.

The important question for OTDD is not merely whether a source can be
represented as RDF. It is:
>What representation preserves the source structure and governed meaning
> while moving the source knowledge into a form suitable for further knowledge
> engineering?

### CSV on the Web (CSVW)

CSVW is the W3C family of Recommendations for tabular data and metadata. 
Its tabular model explicitly covers CSV-like sources as well as spreadsheets,
HTML tables, fixed-field files, and SQL-derived tabular data.

It provides concepts for tables, rows, columns, cells, datatypes, titles, keys,
foreign keys, annotations, and metadata, and supports conversion of annotated
tabular data into RDF and JSON.

#### Best fit: 
Governed sources that are fundamentally tabular.

#### Limits: 
It does not reproduce the complete Excel workbook object model, and it does
not by itself supply domain-specific constraint semantics.

### PROV-O

PROV-O is the W3C OWL ontology for provenance. 
It represents entities, activities, agents, derivations, generations, uses,
and attribution.

#### Best fit: 
Preserving traceability from normalized knowledge back to governed source
artifacts and transformation activities.

#### Limits:
It does not model table structure or constraint logic; it complements other
representations.

### DCAT

DCAT is the W3C vocabulary for describing datasets, distributions, data services,
and catalogs.

#### Best fit: 
Dataset-level governance, publication, discovery, versioning, and distribution 
metadata.

#### Limits: 
It does not primarily describe individual spreadsheet rows or cells and does
not model constraint logic.

### RDF Data Cube Vocabulary

The RDF Data Cube Vocabulary represents multidimensional observations
organized by dimensions, measures, and attributes.

#### Best fit: 
Statistical, observational, OLAP, and tensor-like datasets.

#### Limits: 
A general requirement spreadsheet is not naturally an observation cube; 
using Data Cube for ordinary constraint rows may introduce unnecessary
machinery.

### SKOS

SKOS is the W3C model for concept schemes, controlled vocabularies, taxonomies,
thesauri, labels, and semantic relationships among concepts.

#### Best fit: 
Governed enumerations, classifications, categories, severity schemes, 
and term mappings.

#### Limits: 
It does not model source table structure, detailed provenance, or executable
validation.

### PROF

The W3C Profiles Vocabulary describes profiles of specifications and the
resources that make up those profiles, including schemas, validation resources,
guidelines, and term lists.

#### Best fit: 
Organizing and publishing a validation profile and its component artifacts.

#### Limits: 
As of 2026 it is a W3C Working Draft, and it does not supply row-level 
constraint semantics.

### SHACL

SHACL describes and validates conditions over RDF graphs.

#### Best fit: 
Executable RDF validation after governed identity, meaning, applicability,
provenance, and expected behavior have been established.

#### Limits: 
SHACL is an implementation representation; using it as the sole Governed
Constraint Representation risks collapsing source evidence, normalized meaning,
and executable implementation into one artifact.

### Project-defined RDF vocabulary

A project may define a small RDF vocabulary for normalized constraint
semantics that are not adequately expressed by existing standards.

Candidate concepts include governed constraint, requirement statement,
applicability condition, violation condition, governed severity, source
identifier, implementation relationship, and links to schema resources.

#### Best fit: 
Filling only the semantic gap left after suitable standards have been applied.

#### Limits: 
The project must govern the vocabulary, and unnecessary invention should be
avoided.

### Non-RDF normalized representations

JSON, YAML, relational tables, Python objects, or other structured forms may
also serve as intermediate representations when they preserve governed
identity, meaning, applicability, severity, and provenance and remain
testable.

OTDD does not require every intermediate representation to be RDF.

### Representation composition

The options above are not mutually exclusive. 
A mature Governed Constraint Representation may combine:

- CSVW for source tabular structure;
- DCAT for dataset and distribution identity;
- PROV-O for derivation and provenance;
- SKOS for controlled vocabularies;
- a small constraint vocabulary for normalized requirement semantics;
- PROF for specification/profile packaging; and
- SHACL for executable validation.

The selection question is often not:

>Which one standard wins?

It is:

>Which standards occupy which roles in the representation, and what
> project-specific semantics remain after those standards are applied?

## References

R1. W3C, Model for Tabular Data and Metadata on the Web: https://www.w3.org/TR/tabular-data-model/

R2. W3C, Metadata Vocabulary for Tabular Data: https://www.w3.org/TR/tabular-metadata/

R3. W3C, PROV-O: The PROV Ontology: https://www.w3.org/TR/prov-o/

R4. W3C, Data Catalog Vocabulary (DCAT) - Version 3: https://www.w3.org/TR/vocab-dcat-3/

R5. W3C, The RDF Data Cube Vocabulary: https://www.w3.org/TR/vocab-data-cube/

R6. W3C, SKOS Simple Knowledge Organization System Reference: https://www.w3.org/TR/skos-reference/

R7. W3C, Shapes Constraint Language (SHACL): https://www.w3.org/TR/shacl/

R8. W3C, The Profiles V