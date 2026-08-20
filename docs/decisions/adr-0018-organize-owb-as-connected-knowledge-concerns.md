# ADR-0018: Organize OWB as Connected Knowledge Concerns

## Status

Proposed

## Date

2026-08-19

## Context

The Ontology Workbench (OWB) ecosystem represents several kinds of knowledge:

- shared domain meaning expressed through ontologies;
- specification and profile applicability;
- executable constraints and their business meaning;
- facts projected from source documents and other inputs;
- provenance linking knowledge to its authoritative sources; and
- execution evidence produced by validation and other processes.

These kinds of knowledge are closely connected. A constraint governs an
ontology term. A validation result identifies the constraint that was
evaluated and the instance fact that caused the result. An applicability
assertion connects a specification release to the shared concepts it uses.
Provenance connects each of these resources to its source and governing
decision.

Describing these concerns as semantic "layers" creates false geometry. The
term suggests vertically stacked containers, a fixed dependency direction,
and isolation between levels. Those implications do not describe an RDF
knowledge graph, in which statements connect resources across every such
boundary.

OWB nevertheless needs practical boundaries for provenance, versioning,
access control, lifecycle management, publication, deployment, and query
construction. RDF datasets and named graphs can provide those boundaries, but
their operational purpose must not be mistaken for semantic separation.

The UAD project makes this issue immediate. UAD constraints originate in
specifications and spreadsheets, apply to governed shared MISMO ontology
terms, execute against appraisal instance graphs, and produce results that
must carry both business and technical meaning. Treating a SHACL file as an
adjacent implementation artifact would omit much of that knowledge and weaken
traceability.

## Decision

### One Connected Knowledge Graph

OWB shall treat its governed RDF content as a connected knowledge graph.
Ontology meaning, specification applicability, executable constraints,
instance facts, provenance, and execution evidence shall be modeled as
connected knowledge concerns rather than as hierarchical semantic layers.

A knowledge concern identifies a responsibility or subject of knowledge. It
is not a container, storage tier, processing stage, or direction of
dependency.

Resources in one concern may and normally will refer directly to resources in
other concerns. For example:

- a UAD applicability assertion may identify a shared MISMO ontology term;
- a SHACL property shape may use a shared MISMO property as its `sh:path`;
- a constraint may identify its source specification, spreadsheet row, and
  governing release;
- a validation result may identify the constraint, focus node, value, and
  pipeline execution that produced it; and
- an explanation may combine domain meaning, the constraint's business
  message, the offending instance fact, and provenance.

No intermediate copy or parallel identity shall be introduced merely to keep
these concerns separate.

### Constraints Are Governed Knowledge

Executable constraints shall be first-class resources in the knowledge
graph. Their SHACL statements are part of their RDF representation, not an
unrelated configuration format.

A governed constraint shall be able to carry, when applicable:

- a stable IRI;
- its SHACL shape and constraint statements;
- the ontology class or property it governs;
- its business definition;
- business-facing and technical messages;
- severity;
- source rule, spreadsheet row, or specification reference;
- provenance and governing a publication version;
- lifecycle status and effective period;
- applicability to a specification or profile; and
- links from validation results and execution evidence.

A SHACL engine may receive a selected shapes graph assembled from this
knowledge. That operational selection does not make the extracted graph the
conceptual authority for the constraints.

### Named Graphs Are Governance Partitions

Named graphs may partition an OWB RDF dataset when a boundary is needed for:

- provenance;
- versioning;
- publication or deployment;
- access control;
- lifecycle management;
- replacement and rollback;
- source attribution; or
- construction of an executable or query-specific view.

Named graphs shall not be treated as semantic layers. A named graph does not
own the identities of the resources mentioned within it, and its boundary
does not prohibit RDF links to resources described in another named graph.

A knowledge concern and a named graph are not required to have a one-to-one
relationship. One concern may be partitioned across multiple governed named
graphs, and one named graph may contain statements relevant to more than one
concern when its project governance purpose requires that grouping.

The selection of graph IRIs, graph versioning rules, default-graph behavior,
and deployment-specific dataset layout may be governed by later decisions.
Consumers shall not assume that the default graph is automatically the union
of all named graphs. Applications and queries shall select or construct the
required view explicitly.

### Files Are Serializations and Deployment Artifacts

Turtle, RDF/XML, JSON-LD, SHACL Turtle, and other files remain valid means of
exchange, review, source control, testing, publication, and deployment.

A file shall be treated as a serialization or package of governed graph
content, not as the conceptual home or identity boundary of the knowledge it
contains. Moving the same governed RDF statements between a repository file,
an RDF database, and an API response shall not change the identities or
meaning of their resources.

When a canonical file artifact is required, its canonical status shall be
governed explicitly. Canonical status does not make the file path part of the
identity of the serialized resources.

### Views Are Purpose-Specific Selections

Applications may construct views or subgraphs for a defined purpose,
including:

- SHACL validation;
- business explanation;
- developer diagnostics;
- specification coverage analysis;
- provenance review;
- publication; and
- execution reporting.

A view selects knowledge; it does not establish a new semantic layer. Unless
explicitly governed otherwise, a view shall reuse the IRIs of the selected
resources and preserve sufficient provenance to identify its source graphs
and governing versions.

### Terminology and Diagrams

Architecture documentation shall use terms such as "knowledge concern,"
"named-graph organization," "governance partition," and "view" when those
meanings are intended.

The term "layer" may still be used for genuine software architecture, such as
user-interface, service, and persistence layers. It shall not be used to
imply that OWB semantic content forms a vertical hierarchy.

Diagrams of the knowledge graph should emphasize connected resources and
cross-concern relationships. Boxes or colors may identify concerns or named
graphs, but their legends shall state whether they represent meaning,
governance, deployment, or a query view.

### Implementation Discipline

Implementations of the preceding UAD architecture decisions have followed
Behavior-Driven Development (BDD) and Test-Driven Development (TDD)
discipline. That discipline shall continue.

Beginning with this decision, implementation of an ADR that introduces or
changes governed knowledge shall also follow Ontology Test-Driven Development
(OTDD) discipline. OTDD supplements BDD and TDD; it does not replace either
one.

Before an implementation of this decision is declared complete:

1. the relevant business meaning and terminology shall be stated and reviewed;
2. competency questions or equivalent semantic acceptance criteria shall be
   identified;
3. ontology tests shall demonstrate the missing or incorrect semantic behavior;
4. BDD scenarios shall trace the required behavior to this decision;
5. software tests shall drive the implementation through the ordinary TDD
   red-green-refactor cycle; and
6. the resulting ontology, constraint, provenance, and execution relationships
   shall satisfy the ontology tests and competency questions.

Ontology tests shall evaluate meaning expressed in RDF, including the required
resource identities and relationships across knowledge concerns. They shall
not be limited to confirming that a Turtle file parses, that particular text
appears in serialization, or that application code executed without error.

For the first constraint-knowledge implementation governed by this decision,
the OTDD evidence shall include tests showing that:

- a governed constraint is represented as an identifiable knowledge resource;
- its executable SHACL statements govern the intended shared MISMO term;
- its business meaning, technical meaning, applicability, and provenance
  remain queryable;
- a validation result can identify both the governing constraint and the
  affected appraisal fact; and
- named-graph or file boundaries do not require duplicate semantic identities.

An ADR implementation shall not be marked complete solely because its BDD and
TDD tests pass when the decision also changes the meaning or organization of
governed knowledge. Its traceability record shall identify the corresponding
OTDD evidence.

## Consequences

### Positive

- Constraints retain their executable SHACL form, business meaning,
  provenance, applicability, and lifecycle as one connected body of
  knowledge.
- Validation results can identify the exact governed rule and instance facts
  involved.
- Shared MISMO ontology terms retain one identity across UAD constraints,
  appraisal instances, and other OWB projects.
- SPARQL queries can cross ontology, applicability, constraint, instance,
  provenance, and execution concerns.
- Named graphs can support operational governance without fragmenting
  semantic identity.
- File-based development and RDF-database deployment can use the same IRIs and
  statements.
- Purpose-specific views can be assembled without copying or renaming domain
  concepts.
- Architecture language will distinguish semantic relationships from software
  or storage architecture.
- Architectural changes to governed knowledge will be checked for semantic
  correctness as well as behavioral and software correctness.

### Negative

- Dataset queries must deliberately select the named graphs or constructed
  view they require.
- Access control and graph publication policies must account for links that
  cross named-graph boundaries.
- Constraint ingestion must preserve more than executable SHACL triples when
  business meaning and provenance are available.
- Implementations must prevent deployment packaging from becoming an
  accidental second identity system.
- Developers must understand the distinction between a knowledge concern, a
  named graph, a serialized file, and a constructed view.
- ADR implementation requires competency questions and ontology tests in
  addition to the existing BDD and TDD evidence when governed meaning changes.

### Neutral

- This decision does not require all RDF statements to be stored in one
  physical database.
- This decision does not require every deployment to use the same named-graph
  layout.
- This decision does not prohibit standalone SHACL files; it defines them as
  serializations or deployment packages of governed constraint knowledge.
- This decision does not select a particular RDF database or SHACL engine.
- This decision does not establish the final graph-IRI or dataset-versioning
  policy.
- OTDD complements rather than replaces the project's existing BDD and TDD
  workflow.

## Implementation Guidance

The initial UAD implementation should be capable of maintaining distinguishable
but connected graph content for:

- the governed shared MISMO ontology;
- UAD release applicability;
- UAD constraints and their provenance;
- each appraisal instance;
- each validation or pipeline execution; and
- the results and explanations produced by that execution.

The exact named-graph packaging may evolve, but the following relationships
shall remain possible without lexical matching or file-path inference:

```text
MISMO term <- UAD applicability
MISMO term <- SHACL constraint
SHACL constraint <- source rule or spreadsheet row
SHACL constraint <- validation result -> appraisal fact
validation result -> pipeline execution
```

Constraint conversion from the UAD data-constraints spreadsheet should
therefore produce both:

1. executable SHACL statements; and
2. governed rule metadata, provenance, applicability, and audience-specific
   messages linked to those statements.

Tests should verify the semantic relationships independently of Turtle
serialization order and physical file location.

## Alternatives Considered

### Organize Semantic Content as Layers

Rejected because the metaphor implies a vertical order, fixed dependency
direction, and separation that do not exist in the connected RDF model.

### Keep Constraints Only in an Adjacent SHACL File

Rejected because executable syntax alone does not provide the full identity,
business meaning, provenance, applicability, lifecycle, and execution
traceability required of governed rules.

### Put Every Concern in One Undifferentiated Graph

Rejected because provenance, versioning, access, deployment, lifecycle, and
rollback may require explicit graph boundaries. Connected semantics do not
eliminate operational governance requirements.

### Prohibit Links Across Named Graphs

Rejected because named graphs are partition statements, not resource identity.
Preventing cross-graph references would fragment shared concepts and obstruct
traceability.

### Treat Repository Files as the Authoritative Knowledge Boundaries

Rejected because file paths and packaging are deployment concerns. The same
governed knowledge must remain identifiable when serialized differently or
loaded into an RDF database.

### Copy Knowledge into Separate Application-Specific Models

Rejected as the default approach because copied concepts and rules can drift,
lose provenance, and acquire competing identities. Purpose-specific views
should select and reuse governed resources unless a separate transformation is
explicitly required and traced.

## Related Decisions and Features

- ADR-0005: Single Logical Ontology
- ADR-0014: RDF Representation of XML Schema Components
- ADR-0015: SHACL Representation of XML Schema Components
- ADR-0017: IRI and Collision Policy
- `docs/methodology/otdd-development-flow.md`
- `features/logical_schema_to_ontology.feature`
- `features/uad_xml_to_rdf_instance.feature`
