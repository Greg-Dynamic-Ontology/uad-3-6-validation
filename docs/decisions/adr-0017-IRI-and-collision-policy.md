# ADR-0017: IRI and Collision Policy

## Status

Accepted

## Date

2026-08-17

Amended 2026-08-19 to establish a shared Dynamic Ontology MISMO namespace
and clarify that UAD is a proper subset of the MISMO reference model.

## Context

The UAD 3.6 Validation project projects a neutral Logical Schema Model into
RDF and OWL resources. The projection must assign stable identities to schema
source documents, XML Schema components, shared MISMO concepts, and other
authoritative ontology terms.

UAD is a proper subset of the MISMO reference model. Every UAD domain concept
is therefore a MISMO concept and must retain one governed ontology identity
wherever it is reused. Minting a parallel UAD domain ontology term would
fragment that identity and make cross-project integration harder.

Dynamic Ontology is the umbrella authority for work products from multiple
projects. Separate paths beneath `https://dynamicontology.com/` identify
shared vocabularies and project-specific vocabularies without requiring a
separate domain name for every project.

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
https://dynamicontology.com/
```

ADR-0005 establishes one logical UAD ontology. This ADR extends those accepted
decisions for schema sources, schema components, shared MISMO concepts, local
declarations, anonymous types, projected ontology terms, and collision
handling.

## Decision

### Dynamic Ontology as the Umbrella Authority

Dynamic Ontology shall remain the persistent IRI authority for governed work
products created by this ecosystem. Project and vocabulary identity shall be
expressed through stable paths beneath:

```text
https://dynamicontology.com/
```

A separate registered domain is not required merely because a vocabulary is
shared by more than one project. Any additional domain may provide branding,
discovery, or redirection, but it shall not silently introduce a second
canonical identity for the same resource.

### Shared MISMO Ontology Terms

Every domain ontology concept represented by UAD shall use the shared governed
MISMO ontology namespace:

```text
https://dynamicontology.com/mismo/ontology#
```

The same shared MISMO IRI shall be reused by UAD and by other Dynamic Ontology
projects that use the same concept. UAD shall not mint a parallel UAD domain
term merely because the concept was encountered through a UAD schema.

A schema component shall project to a MISMO ontology term only when that
mapping is governed and reproducible. A matching lexical name alone shall not
establish the mapping. A component without a governed MISMO mapping shall
remain explicitly unresolved and shall not receive an invented UAD domain
ontology term.

The namespace `https://dynamicontology.com/uad36/ontology#` shall not be used
for projected MISMO domain concepts. UAD-specific shapes, rules, profile
metadata, provenance, and execution resources may use their separately
governed UAD namespaces.

These Dynamic Ontology MISMO IRIs constitute the governed RDF representation
derived from MISMO specifications. They shall not be represented as
officially issued by MISMO unless MISMO has adopted or published them as such.

If MISMO publishes an authoritative RDF IRI for a concept, that published IRI
shall be evaluated for direct reuse. Any equivalence, replacement, or
supersession relationship shall be governed explicitly.

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

The corresponding MISMO ontology term shall use:

```text
https://dynamicontology.com/mismo/ontology#
```

The projected ontology term shall identify its originating schema component.
The schema component shall retain its source QName, component kind, and
governed source-document IRI.

Separating schema-component and ontology-term identities permits the
structural schema model and semantic ontology to evolve independently without
losing traceability. Reusing shared MISMO ontology-term IRIs permits UAD and
other derivative projects to share semantic identity. An unresolved schema
component remains a schema resource without a fabricated domain term.

### Authority for Projected Terms

The project shall mint authoritative terms only under namespaces controlled by
Dynamic Ontology.

The XML Schema target namespace, including the MISMO residential namespace,
shall be preserved as part of the source QName and provenance. It shall not be
treated automatically as an RDF vocabulary or used as the minting authority
for project-created ontology terms.

The governed shared MISMO ontology namespace does not manufacture terms under
a MISMO-controlled domain. It provides one Dynamic Ontology identity for
concepts derived from MISMO specifications and reused across projects.

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
that the name is unambiguous and the schema-to-MISMO mapping is governed.
Clean naming shall never cause two distinct schema components to merge
silently.

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

Anticipated collisions shall be prevented through component kind, source
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

### Identity Across Schema Revisions and Projects

A named semantic component shall retain its ontology-term IRI while its
governed semantic key and MISMO mapping remain the same.

Changes to documentation, facets, contained declarations, source filenames,
or physical locations shall not by themselves change the ontology-term IRI.
Those changes shall be recorded through provenance and version metadata.

Source-document IRIs remain content-addressed and therefore change whenever
the exact source bytes change.

Content hashes shall identify source artifacts and supporting evidence. They
shall not be used as the primary identity of named ontology terms.

A MISMO concept shall retain the same shared MISMO ontology IRI when reused by
UAD or another project. Because UAD is a proper subset of MISMO, this project
does not mint UAD-specific domain concepts. Any future requirement for a
non-MISMO domain concept requires a separate architectural decision.

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

Established RDF, RDFS, OWL, XML Schema, and other authoritative vocabulary
IRIs shall be reused when they directly identify the required external
concept.

MISMO XML QNames, XLink identifiers, and other external identifiers shall be
preserved as provenance or alignment evidence. An XML namespace shall not be
converted automatically into an RDF vocabulary namespace.

The project shall not mint new resources under domains or namespaces it does
not control.

An explicit alignment may relate a governed Dynamic Ontology term to an
external term. A lexical name match alone shall not establish equivalence.

### Required Identity Evidence

Every projected ontology term shall retain sufficient evidence to reproduce
and audit its identity. The evidence shall include, when applicable:

- projected ontology-term IRI;
- governed schema-to-MISMO mapping status;
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

Given the same Logical Schema Model, governed schema-to-MISMO mappings, and
minting-policy version, the projector shall produce:

- the same schema-component IRIs;
- the same shared MISMO ontology-term IRIs;
- the same unresolved mapping dispositions;
- the same collision dispositions; and
- an equivalent ontology graph.

IRI generation shall not depend on iteration order, memory addresses, random
values, temporary directories, repository layout, or RDF serialization order.

## Consequences

### Positive

- Schema structure and ontology meaning have distinct, traceable identities.
- MISMO concepts retain one identity across UAD and other projects.
- Unresolved schema components remain visible rather than creating parallel
  UAD domain concepts.
- Generated IRIs remain independent of physical storage and deployment.
- Local declarations and anonymous types receive reproducible identities.
- Name collisions cannot silently corrupt the ontology.
- Source revisions remain auditable without forcing semantic identity churn.
- Projected terms do not imply ownership by MISMO or another external party.
- File artifacts and RDF database graphs can refer to the same resources.
- No additional domain registration is technically required.

### Negative

- Projection requires an explicit semantic-key and collision registry.
- Projection requires a governed schema-to-MISMO mapping where that mapping
  cannot be established safely from existing evidence.
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
- An additional domain may redirect to the governed namespace for branding or
  discovery, but it does not create another canonical term identity.

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

Existing projected domain ontology terms shall migrate to the shared MISMO
ontology namespace:

```text
https://dynamicontology.com/mismo/ontology#
```

IT-7R3S1 shall require that:

- every projected domain ontology term uses the governed shared MISMO
  ontology namespace;
- schema components use the governed UAD schema-resource namespace;
- each projected ontology term identifies its originating schema component;
- the source target namespace remains preserved as source identity and
  provenance; and
- no project-created term is minted under an uncontrolled source namespace;
  and
- any schema component without a governed MISMO mapping remains explicitly
  unresolved.

No historical artifact shall be edited merely to disguise the migration.
Superseded IRIs shall be related explicitly if they have been published or
consumed externally.

## Alternatives Considered

### Use the XML Schema Target Namespace as the IRI Authority

Rejected because an XML namespace is not automatically an RDF vocabulary and
the project does not control the MISMO schema namespace.

### Mint Projected Domain Terms Under the UAD Ontology Namespace

Rejected because UAD is a proper subset of MISMO and its domain concepts would
acquire duplicate identities.

### Require a Separate Domain for the Shared MISMO Ontology

Rejected because Dynamic Ontology already provides a controlled umbrella
authority. A stable path beneath that authority supplies the required
separation without another domain and another persistence obligation.

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
