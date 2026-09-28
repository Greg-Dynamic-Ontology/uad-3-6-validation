# UAD 3.6 Validation — Architecture

## Purpose and Evidence Boundary

This document describes the project's principal components, information flows,
and architectural boundaries. It distinguishes accepted architectural direction
from behavior visible in the implementation reviewed on 2026-09-27.

It is a review draft derived from local source code and project documentation.
No application execution or test-suite run was performed for this document;
implementation observations do not establish operational readiness or complete
rule coverage. Iteration progress and current test results belong in
`CURRENT-STATE.md`.

## Governing Principles

**Derivation, not divination.**

Validation behavior and semantic identities should be derived from governed
sources. Missing or ambiguous knowledge must remain explicit rather than be
replaced by invented meaning.

The project validates UAD appraisal XML against the GSE UAD-specific schema and
governed business constraints. The original published MISMO 3.6 schema is not
the production validation authority. Shared MISMO domain identity does not
make the two XML schema sets validation-compatible.

ADR-0008 establishes RDF+/OWL as the canonical internal semantic representation.
Parser trees, Python objects, caches, and validation events may support
computation but are not intended to become independent authorities for meaning.
Some current application paths still operate directly on XML and Python models;
the accepted architecture is therefore broader than the integration presently
visible in the API.

Deterministic validators own compliance decisions. AI assistance is advisory.
ADR-0007 specifies OTDD validation of explicit RDF instance assertions with
`inference="none"`; inference may be tested separately when it is the subject
under test.

## Component Organization

| Location | Responsibility |
| --- | --- |
| `../../app/main.py` | Creates the FastAPI application, installs the API router, and serves `../../site`. |
| `../../app/api/routes.py` | Exposes ingestion, schema validation, RDF projection, selected business validation, results, and advisory endpoints. |
| `../../app/models` | Defines application request/result models and the Logical Schema Model. |
| `../../app/services/schema_loader` | Loads schema structures with separate modules for closure, declarations, groups, derivations, and processing policy/coverage. |
| `../../app/projections` | Contains schema/RDF and Logical Schema-to-ontology projections. |
| `../../app/services` | Contains validation, RDF projection, constraint construction, governance, and customer/account services. |
| `../../app/generators` | Contains vocabulary generation for simple types, complex types, and arcroles. |
| `../../app/adapters` | Provides the current resource/rule store and advisory LLM boundary. |
| `../../app/core` | Holds configuration, namespaces, and identity utilities. |
| `../../features` and `tests/` | Hold behavioral specifications and executable evidence. |
| `../../docs/decisions` | Records architectural decisions. |

The declared runtime is Python 3.11 or later. Principal dependencies include
FastAPI, Pydantic, xmlschema, RDFLib, pySHACL, and openpyxl. Dependency presence
does not by itself establish that a capability is integrated into an API path.

## Governed Schema and Knowledge Preparation

The schema-validation service and Logical Schema generation service select:

```text
specs/UAD/GSE_UAD_3.6.0_v1.3/Combined/GSE_UAD_3.6.0_v1.3.xsd
```

Schema preparation and appraisal processing are distinct flows:

```text
Governed UAD XSD
    -> SchemaLoader
    -> Logical Schema Model
    -> Logical Schema RDF/Turtle

Logical Schema Model
    -> governed ontology projection
    -> shared MISMO ontology terms and schema provenance
```

`../../app/services/generate_logical_schema_graph.py` loads the model and serializes
it through `logical_schema_serializer.py`. Its default output is
`docs/milestones/milestone-1/artifacts/logical-schema.ttl`.

The Logical Schema represents source structure; the ontology projection adds
governed semantic interpretation. These artifacts should not be conflated with
an RDF graph representing an individual appraisal.

## Identity and Namespace Boundaries

ADR-0017 distinguishes source documents, schema components, and projected
ontology terms. It requires governed, reproducible mappings and collision-aware
identity construction. A matching local name alone is insufficient evidence
for a semantic mapping.

| Identity concern | Namespace or policy |
| --- | --- |
| Shared MISMO domain concepts | `https://dynamicontology.com/mismo/ontology#` |
| UAD schema projection resources | `https://dynamicontology.com/uad36/schema#` |
| Logical Schema model vocabulary | `https://dynamicontology.com/uad36/schema-model#` |
| Existing UAD ontology vocabulary | `https://dynamicontology.com/uad36/ontology#` |
| Schema source documents | `https://dynamicontology.com/uad36/source/sha256/` followed by the source-byte digest |

`../../app/core/schema_source_iri.py` implements content-addressed source document
identity. `app/projections/logical_schema_to_ontology.py` implements shared
MISMO ontology projection and identifies ADR-0017 as its minting policy version.
The existing UAD vocabulary remains in code, including execution metadata;
its presence does not override ADR-0017's shared-domain identity decision.

Source namespace, local name, component kind, and ownership context must remain
available where needed to distinguish schema resources. Source-component
identity and projected domain-concept identity serve different purposes.

## Appraisal Processing: Current API Paths

### XML schema validation

`POST /validate/uad36/xml-schema` passes uploaded bytes to
`validate_uad36_xml_bytes`. The service uses the governed UAD XSD and returns a
`SchemaValidationReport` with well-formedness, schema validity, summary, and
findings. Source locations are recorded where available; a missing child may
be located through its nearest known ancestor.

Schema validity establishes structural conformance, not satisfaction of all
governed business constraints.

### RDF instance projection

`RdfProjectionStage` accepts a `LoadedAppraisal` and delegates to `RdfProjector`.
The projector supports an ontology-aware mode and a legacy name-mapping mode.
The inspected API routes instantiate `RdfProjector()` without supplying an
ontology, so those routes currently use the legacy mode.

`POST /validate/uad36/rdf-projection` returns the package name, completion status,
and triple count. `POST /validate/uad36/pipeline` currently accepts only the
`rdf-projection` pipeline selection. It records a run and source-byte SHA-256
on success; projection failure is represented through an execution RDF graph
and a business-facing error response.

Completion of this pipeline means projection completed. It does not establish
that schema validation or SHACL business validation was also performed.

### Selected business-rule validation

`POST /validate/uad36` and its Fannie/Freddie variants invoke
`ValidationService.validate`. That method parses XML, requires a UAD
`VALUATION_ANALYSIS` context, and calls the required-data evaluator.

`../../app/services/required_data.py` reads `data/data-constraints.csv`. It supports
Fatal unconditional requirements, explicitly mapped single-equality
requirements, and selected conditional/scoped rules. It checks supported
definitions and contexts rather than implementing a general interpreter for
every source row.

This path returns findings with severity, location, expected condition, and
source provenance, summarized in a validation run. It does not call the full
XSD-validation service or execute a general SHACL constraint set. Investor
scope endpoints alone do not establish complete coverage for either GSE.

## Accepted Validation Pipeline Direction

ADR-0013 describes the intended semantic validation and reporting flow:

```text
UAD XML
    -> canonical RDF instance graph
    -> governed SHACL validation
    -> findings and measurements
    -> reports and dashboards
    -> historical analytics
    -> optional AI assistance
```

Each stage is intended to produce traceable artifacts for downstream use.
Reports and measurements are product outputs derived from deterministic
validation evidence. The complete connected flow above must not be inferred
from the existence of individual services or feature files.

## Governed Constraint Construction

Constraint construction is a separate concern from validating a submitted
appraisal. It transforms governed requirements into justified executable
constraints.

`../../docs/otdd/uad-governed-constraint-representation.md` selects a composed RDF
representation: CSVW for tabular source evidence, PROV-O for derivation, a small
governed vocabulary for normalized constraint semantics, and SHACL for the
eventual executable validation representation.

Normalization must preserve source artifact and row identity, original values,
governed rule identity, requirement, applicability, violation condition,
severity, source locator, and relationships to Logical Schema resources.
The normalized requirement remains distinct from its executable SHACL form.

Inspected implementation provides:

- normalization into RDF with required-field and ambiguity checks in
  `constraint_normalization_agent.py`;
- ordered construction-stage advancement that stops at the first unverified
  stage in `constraint_construction_process.py`;
- RDF stage-result identities, statuses, and provenance support in
  `construction_exchange.py`;
- governed batch member materialization and result-graph persistence support
  in `governed_batch_execution.py`.

The feature set under `../../features/constraint-production` describes normalization,
RDF exchange, Logical Schema binding, context resolution, behavior
classification, instance-RDF binding, SHACL generation, finding projection,
and pipeline execution. These specifications express required behavior;
this review does not certify completion of every stage or batch.

## Storage, Presentation, and Advisory Boundaries

The current `InMemoryGraphStore` holds resource and rule objects in Python
dictionaries. `ValidationService` likewise keeps runs, findings, and execution
graphs in memory. These API stores do not establish durable database storage.
Separate services can serialize knowledge artifacts to files; that is a
different persistence mechanism.

The FastAPI application serves `../../site`. Presentation capabilities are read from
the RDF configuration selected through `config/configuration.ttl`, including
whether to expose pipeline stages, technical artifacts, and developer
diagnostics. Presentation policy should not be mistaken for authorization.

`../../app/adapters/llm.py` is explicitly an advisory placeholder for Ollama/RAG.
Its inspected methods construct explanations and revision-history comments;
they do not establish a live model integration or own compliance decisions.

## OTDD and Collaboration

UAD 3.6 is a proving ground for Ontology Test-Driven Development and the
experimental `chatgpt-sources/` collaboration model.

OTDD makes evidence for software and knowledge behavior explicit through
behavioral specifications, executable tests, and semantic artifacts.
`chatgpt-sources/` makes the evidence supplied to an AI collaborator explicit.
Both support traceable derivation from governed sources.

Authoritative artifacts remain in their normal project locations.
`chatgpt-sources/input/` supplies task material, `chatgpt-sources/context/`
holds durable context, and `chatgpt-sources/work/` holds proposals pending
Greg's review and promotion. The collaboration directory is not a runtime
component or an independent authority for validation rules.

## Maintenance References

Reconcile this overview against the following project sources when behavior or
decisions change:

- `../../README.md` and `pyproject.toml` for scope and runtime declarations;
- ADR-0007, ADR-0008, ADR-0013, and ADR-0017 for validation, semantic authority,
  pipeline direction, and identity policy;
- `../../app/api/routes.py` for actual public-path composition;
- the schema, projection, validation, constraint-construction, and storage
  modules identified above for implementation evidence;
- `../../features` and `tests/` for required behavior and its executable evidence.

Keep project purpose in `PROJECT-CONTEXT.md`, changing progress in
`CURRENT-STATE.md`, and detailed OTDD working rules in their dedicated
conventions and methodology documents.
