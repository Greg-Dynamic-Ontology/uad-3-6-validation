# UAD 3.6 Validation — Project Context

## Project

Repository:

    uad-3-6-validation

Local development root:

    C:\Users\grego\projects\uad-3-6-validation

The project validates UAD 3.6 appraisal XML instances against governed
business rules and produces measurable validation results.

The immediate objective is a usable MVP that can validate appraisal data
against deterministic UAD business constraints.

The longer-term objective is a meaning-first validation and knowledge system
in which schemas, constraints, ontologies, validation results, and provenance
can be represented and reasoned about consistently.

## Primary Principle

Derivation, not divination.

Project behavior should be derived from governed source material whenever
possible rather than inferred from undocumented assumptions.

## Project as a Proving Ground

UAD 3.6 Validation serves as a proving ground for two related working models:
Ontology Test-Driven Development (OTDD) and the experimental
`chatgpt-sources/` collaboration model.

### OTDD

UAD is the primary proving ground for developing and testing OTDD practices,
including:

- iteration, rule, and scenario organization;
- RED and GREEN behavior;
- rule and commit boundaries;
- treatment of governed sources;
- testing of semantic artifacts;
- identification of practices suitable for reuse by other projects.

### ChatGPT Sources

UAD is also a proving ground for developing and testing the
`chatgpt-sources/` collaboration model.

The experiment is intended to determine:

- what project context should always be available to ChatGPT;
- what governed sources should be directly available;
- what belongs in task-specific input;
- where AI-produced work should be placed;
- how authoritative artifacts are distinguished from AI-accessible copies;
- how much of a project should be exposed to an AI collaborator;
- which practices are sufficiently successful to reuse in other projects.

The current `chatgpt-sources/` structure is experimental rather than a
finished project standard. Its effectiveness should be evaluated through
actual UAD development work before the pattern is generalized to other
projects.

### Common Principle

OTDD makes the evidence for software and knowledge behavior explicit.

`chatgpt-sources/` makes the evidence supplied to an AI collaborator explicit.

Both practices support the project's preference for traceable derivation
from governed sources over undocumented inference:

**Derivation, not divination.**

## UAD and MISMO

UAD 3.6 is derived from MISMO 3.6 but is not treated as validation-compatible
with the complete MISMO schema.

The project uses the GSE-trimmed UAD 3.6 schema as the governed structural
source for UAD validation.

The MISMO schema may be retained as reference material, but validation is
performed against the UAD-specific governed model.

The UAD-specific governed model is a subset of the MISMO model, and
the project does not attempt to validate MISMO-specific content.

## Important Inputs

The project has used or currently uses:

- GSE UAD 3.6.0 v1.3 schema
- GSE UAD XLink schema
- xml.xsd
- UAD sample XML files
- UAD business-rule / data-constraint spreadsheets
- URAR implementation-guide material
- ontology and logical-schema artifacts generated from governed sources

A major constraint inventory contains approximately 729 rows of business
rules.

## Major Artifact Types

The project contains several distinct classes of artifacts:

### Governed source artifacts

Examples:

- XML schemas
- constraint spreadsheets
- implementation-guide material
- sample XML instances

### Behavioral specifications

Stored primarily under:

    features/

Feature files define expected externally observable behavior.

### Executable tests

Stored under:

    tests/

Tests are written with pytest.

### Production code

Stored primarily under:

    app/

### Knowledge artifacts

Stored primarily under:

    ontologies/

These include manually governed ontology material and generated RDF/Turtle
representations.

### Documentation

Stored under:

    docs/

### Published validation site

Stored under:

    site/

## Ontology Direction

The project follows a meaning-first ontology strategy.

Important modeled concepts include:

- Appraisal
- Evidence
- ValuationApproach
- OpinionOfValue
- SubjectProperty
- ComparableSale
- MeasurementRun
- RecordedMeasurement
- IndicationOfValue
- Reconciliation

Important namespace decisions include:

Ontology:

    https://dynamicontology.com/uad36/ontology

Predicate vocabulary:

    https://dynamicontology.com/uad36/predicate#

URAR meaning document:

    https://dynamicontology.com/uad36/urar-meaning

## Logical Schema

The project generates a logical-schema RDF representation of the governed XML
schema.

A critical identity rule is:

Named schema resources preserve governed source identity.

For named XML Schema constructs, source namespace and local name should be
preserved rather than replaced by arbitrary generated identifiers.

Generated identities are reserved for unnamed structures.

This behavior was established during IT-31.

## Business Constraints

The current MVP emphasis is executable deterministic business-rule validation.

An example constraint concerns a required subject-property physical address:

- Primary data element: AddressLineText
- UAD identifier: UAD1001
- Context: Subject Property physical address
- Failure severity: Fatal when required data is absent

The project is moving from structural schema representation toward executable
constraint evaluation against XML instances.

## Development Philosophy

The project favors:

- explicit governed identity;
- stable source-derived identifiers;
- graphs over unnecessary tree-only representations;
- behavior-first development;
- measurable validation results;
- small independently testable rules;
- preservation of provenance;
- deterministic behavior where deterministic rules exist.

The system should report insufficient evidence rather than inventing missing
meaning.

## Collaboration Boundary

The directory:

    chatgpt-sources/

is a controlled collaboration workspace for ChatGPT assistance.

Authoritative project artifacts remain in their normal project locations.

Material placed under:

    chatgpt-sources/input/

is deliberately supplied to ChatGPT for a task.

Material created under:

    chatgpt-sources/work/

is proposed work until reviewed and promoted by the user.

Durable contextual information belongs under:

    chatgpt-sources/context/