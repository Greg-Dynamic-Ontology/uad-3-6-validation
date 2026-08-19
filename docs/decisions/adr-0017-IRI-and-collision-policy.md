# ADR-0017: IRI and Collision Policy

## Status

Accepted

## Date

2026-08-17

## Context

The UAD 3.6 Validation project projects a neutral Logical Schema Model into
RDF and OWL resources. The projection must assign stable identities to schema
source documents, XML Schema components, and authoritative ontology terms.

Several XML Schema conditions prevent a local name alone from being a safe
identifier:

- global declarations of different component kinds may share a name;
- imported namespaces may contain declarations with the same name;
- local declarations may repeat under different owning types;
- anonymous types have no source name;
- source files may be moved, renamed, extracted, or uploaded; and
- schema revisions may change content without changing the intended concept.

IRI generation must remain deterministic while preventing accidental merging.
It must also distinguish the identity of a source schema component from the
identity of the ontology term projected from that component.

ADR-0001 establishes the project ontology namespace. ADR-0002 establishes the
general IRI minting policy and requires project IRIs to be rooted under:

```text
https://dynamicontology.com/uad36/
```

ADR-0005 establishes one logical UAD ontology. This ADR extends those accepted
decisions for schema sources, schema components, local declarations, anonymous
types, projected ontology terms, and collision handling.

## Decision

### Schema Source Documents

A schema source document shall have a content-addressed IRI formed from the
SHA-256 digest of its exact source bytes:

```text
https://dynamicontology.com/uad36/source/sha256/{digest}
```

The physical file path, repository path, filename, extraction directory,
username, operating system, and deployment location shall not contribute to
the IRI.

Identical source bytes shall produce the same source-document IRI regardless
of physical location or filename. Different source bytes shall produce
different source-document IRIs even when the filenames are identical.

The content digest identifies the source artifact. It does not determine the
identity of ontology terms projected from that source.

### Separate Schema-Component and Ontology-Term Identities

An XML Schema component and an authoritative ontology term projected from that
component are distinct resources and shall have distinct IRIs.

Schema-component identities shall use the generated schema-resource namespace:

```text
https://dynamicontology.com/uad36/schema#
```

Authoritative projected ontology terms shall use the controlled UAD ontology
namespace:

```text
https://dynamicontology.com/uad36/ontology#
```

The projected ontology term shall identify its originating schema component.
The schema component shall retain its source QName, component kind, and
governed source-document IRI.

Separating these identities permits the structural schema model and semantic
ontology to evolve independently without losing traceability.

### Authority for Projected Terms

The project shall mint authoritative projected terms only under namespaces it
controls.

The XML Schema target namespace, including the MISMO residential namespace,
shall be preserved as part of the source QName and provenance. It shall not be
used as the minting authority for project-created ontology terms.

This policy avoids implying that Dynamic Ontology may mint authoritative terms
under a MISMO-controlled or other externally controlled domain.

### Global Named Components

The semantic key for a global named schema component shall include:

- its source namespace;
- its XML Schema component kind; and
- its source local name.

The schema-component IRI shall always identify the component kind. A typical
human-readable form is:

```text
https://dynamicontology.com/uad36/schema#complexType-PROPERTY
```

The source namespace remains part of the semantic key even when it is omitted
from the human-readable portion because the component belongs to the primary
UAD schema namespace. Imported or colliding namespaces shall receive a
deterministic namespace qualifier.

Ontology terms may use cleaner semantic names when the projection establishes
that the name is unambiguous. Clean naming shall never cause two distinct
schema components to merge silently.

### Local Declarations

The semantic key for a local declaration shall include:

- the owning component IRI;
- the local component kind;
- the source local name or referenced QName; and
- a deterministic discriminator when the preceding values are insufficient.

A local declaration shall not be identified solely by its local name. It shall
not derive its identity from a filesystem path or raw XPath.

A representative form is:

```text
{owner-IRI}/element-{local-name}
```

When multiple declarations under the same owner would otherwise receive the
same identity, the projector shall add a deterministic discriminator derived
from the normalized Logical Schema Model representation. The discriminator
shall not contain a machine-specific or serialization-specific value.

### Anonymous Types

An anonymous type shall use owner-based identity. Its semantic key shall
include:

- the owning declaration IRI;
- the anonymous-type role; and
- a deterministic discriminator when the owner contains more than one
  anonymous construct of the same role.

A representative form is:

```text
{owning-declaration-IRI}/anonymous-type
```

Anonymous ontology terms shall not use content hashes as their primary
semantic identity. A content digest may be retained as evidence, but the
term's identity shall remain connected to its owning declaration.

### Collision Detection and Response

The projection shall never merge resources silently because their candidate
IRIs collide.

Anticipated collisions shall be prevented through component-kind, source-
namespace, ownership, and deterministic-discriminator qualifiers.

If two distinct semantic keys still produce the same candidate IRI, projection
shall stop with a meaningful error before emitting an ambiguous ontology.

The error shall identify:

- the candidate IRI;
- both semantic keys;
- the source schema components;
- the source documents; and
- the projection operation that detected the collision.

Every collision and its deliberate resolution shall appear in the ontology-
projection reconciliation. An unanticipated collision shall remain visible
until governed by a new or amended decision.

### Identity Across Schema Revisions

A named semantic component shall retain its ontology-term IRI while its
governed semantic key remains the same.

Changes to documentation, facets, contained declarations, source filenames,
or physical locations shall not by themselves change the ontology-term IRI.
Those changes shall be recorded through provenance and version metadata.

Source-document IRIs remain content-addressed and therefore change whenever
the exact source bytes change.

Content hashes shall identify source artifacts and supporting evidence. They
shall not be used as the primary identity of named ontology terms.

A future major model version may introduce a new namespace policy through a
separate ADR. Cross-version equivalence shall be expressed explicitly rather
than inferred from matching local names.

### Case, Escaping, and Normalization

Valid XML local names and their case shall be preserved when used in generated
IRI tokens.

Names differing only by case shall be treated as distinct unless an explicit
governed mapping states that they identify the same concept.

Display labels shall never determine identity.

Characters that cannot be represented safely shall use one documented,
deterministic encoding. Normalization shall not depend on locale, operating
system, filesystem case behavior, or RDF serialization.

### External Namespaces

Established RDF, RDFS, OWL, and XML Schema vocabulary IRIs shall be reused when
they directly identify the required external concept.

UAD projection terms shall use governed UAD IRIs. MISMO QNames, XLink
identifiers, and other external identifiers shall be preserved as provenance
or alignment evidence.

The project shall not mint new resources under domains or namespaces it does
not control.

An explicit alignment may relate a governed UAD term to an external term. A
lexical name match alone shall not establish equivalence.

### Required Identity Evidence

Every projected ontology term shall retain sufficient evidence to reproduce
and audit its identity. The evidence shall include, when applicable:

- projected ontology-term IRI;
- originating schema-component IRI;
- source QName;
- XML Schema component kind;
- owning component IRI for a local or anonymous component;
- governed source-document IRI;
- minting-policy version; and
- collision-resolution discriminator.

The evidence may be stored in the ontology graph, a linked provenance graph,
or the projection reconciliation, provided that it remains queryable and is
linked to the projected term.

## Determinism

Given the same Logical Schema Model and the same minting-policy version, the
projector shall produce:

- the same schema-component IRIs;
- the same ontology-term IRIs;
- the same collision dispositions; and
- an equivalent ontology graph.

IRI generation shall not depend on iteration order, memory addresses, random
values, temporary directories, repository layout, or RDF serialization order.

## Consequences

### Positive

- Schema structure and ontology meaning have distinct, traceable identities.
- Generated IRIs remain independent of physical storage and deployment.
- Local declarations and anonymous types receive reproducible identities.
- Name collisions cannot silently corrupt the ontology.
- Source revisions remain auditable without forcing semantic identity churn.
- Projected terms do not imply ownership by MISMO or another external party.
- File artifacts and RDF database graphs can refer to the same resources.

### Negative

- Projection requires an explicit semantic-key and collision registry.
- Local and anonymous identifiers are less visually simple than global names.
- Some source components require deterministic qualifiers.
- Source-document byte changes create new source IRIs and require provenance
  links to prior versions when continuity matters.
- Existing generated artifacts must be regenerated after this policy is
  implemented.

### Neutral

- Human-readable labels remain separate from identity.
- A term may have several serializations and physical locations without
  changing its IRI.
- External alignment remains a separate deliberate activity.

## Migration Consequences

The provisional schema-source prefix:

```text
https://dynamicontology.com/owb/schema-source/sha256/
```

does not conform to ADR-0002 and shall be replaced with:

```text
https://dynamicontology.com/uad36/source/sha256/
```

The schema-source IRI tests, minting implementation, Logical Schema serializer,
and canonical Logical Schema artifact shall be updated together. The canonical
artifact shall be regenerated deliberately and verified through its
comprehensive comparison test.

IT-7R3S1 currently states that projected resources use IRIs derived from the
schema target namespace. That scenario shall be refined so that:

- projected terms use the governed UAD authority; and
- the source target namespace remains preserved as source identity and
  provenance.

No historical artifact shall be edited merely to disguise the migration.
Superseded IRIs shall be related explicitly if they have been published or
consumed externally.

## Alternatives Considered

### Use the XML Schema Target Namespace as the IRI Authority

Rejected because the project does not control the MISMO namespace and must not
mint project-created terms under an external authority.

### Use One IRI for Both Schema Component and Ontology Term

Rejected because schema structure and projected semantic meaning are different
resources with different evolution and provenance requirements.

### Use Local Names Alone

Rejected because different component kinds, namespaces, owners, and anonymous
constructs can collide.

### Use Filesystem Paths, Filenames, or XPath as Identity

Rejected because those values are storage- or document-layout-dependent and
do not provide durable semantic identity.

### Use Content Hashes for Every Ontology Term

Rejected because ordinary source or documentation changes would unnecessarily
change semantic term identities. Content hashes remain appropriate for source
artifacts and supporting evidence.

### Merge Collisions Automatically

Rejected because lexical equality does not establish semantic equivalence and
silent merging would corrupt the generated ontology.

### Keep the Provisional OWB Schema-Source Prefix

Rejected because it conflicts with ADR-0002 and fragments the established UAD
namespace policy without a demonstrated architectural benefit.

## Related Decisions and Features

- ADR-0001: Project Namespace
- ADR-0002: IRI Minting Policy
- ADR-0005: Single Logical Ontology
- ADR-0014: RDF Representation of XML Schema Components
- ADR-0015: SHACL Representation of XML Schema Components
- `features/logical_schema_to_ontology.feature`
- `features/canonical_logical_schema_artifact.feature`
- `features/governed_schema_source_iris.feature`
