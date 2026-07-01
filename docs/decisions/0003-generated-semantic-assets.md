# Architecture Decision Record 0003: Generated Semantic Assets

**Status:** Accepted

**Date:** 2026-06-29

## Context

The UAD 3.6 Validation project is founded on the principle that the published GSE
artifacts remain the authoritative source of truth.

Examples include:

* XML Schemas (XSD)
* implementation guides
* appendices
* controlled vocabulary spreadsheets
* business rule documents
* sample appraisal packages

The project does **not** manually recreate these artifacts as RDF.

Instead, semantic resources are systematically extracted from the authoritative
sources and represented as RDF.

This approach minimizes manual maintenance, preserves traceability, and ensures
that generated RDF assets remain synchronized with future releases of the
published specifications.

As the Ontology Tool Kit (OTK) evolves, additional semantic extractors will be
implemented. The first implemented extractor generates RDF relationship
predicates from XLink arcrole definitions.

A governing policy is required to distinguish manually authored semantic assets
from generated semantic assets.

---

## Decision

The project shall distinguish between two categories of RDF assets:

### Hand-authored assets

These define the project's semantic architecture and governance.

Examples include:

* ontology vocabulary
* architecture decision records
* namespace policy
* IRI minting policy
* manually authored SHACL templates
* manually authored documentation

These assets are maintained directly by project contributors.

---

### Generated assets

Generated assets are produced deterministically from authoritative source
materials.

Generated assets shall **never** become the source of record.

Instead, they may always be regenerated from the published specifications.

Examples include:

* schema component RDF
* relationship predicate vocabularies
* SKOS concept schemes
* controlled value vocabularies
* validation rule resources
* provenance resources
* appraisal instance graphs
* validation findings

---

## Semantic Extraction Pipeline

Generated assets follow the general pipeline:

```text
Authoritative Source
        ↓
Semantic Extractor
        ↓
IRI Minting
        ↓
Generated RDF Asset
```

The extractor determines the semantic meaning of the source material.

The IRI minting policy assigns stable RDF identifiers.

The resulting RDF assets may be serialized as Turtle, RDF/XML, JSON-LD, or other
supported RDF serializations.

---

## Initial Semantic Extractors

The project begins with a small set of focused semantic extractors.

### Arcrole Vocabulary Generator

Input:

```text
XML Schema (ArcroleBase)
```

Output:

```text
OWL Object Properties
```

Each XLink arcrole enumeration becomes a governed RDF predicate IRI.

Example:

```text
urn:fdc:mismo.org:2009:residential/
DATA_SOURCE_IsDataSourceFor_AccessoryDwellingUnitLegallyRentableIndicator
```

becomes

```text
https://dynamicontology.com/uad36/predicate#
DATA_SOURCE_IsDataSourceFor_AccessoryDwellingUnitLegallyRentableIndicator
```

with preserved provenance back to the originating arcrole URI.

---

### Future Extractors

Future semantic extractors may include:

* XML Schema complex types → OWL classes
* XML Schema elements → schema resources
* XML Schema attributes → datatype properties
* XML Schema enumerations → SKOS concept schemes
* Appendix H → validation rule resources
* XML appraisal packages → RDF instance graphs
* Validation results → validation findings

Each extractor shall follow the same architectural pattern.

---

## Traceability

Every generated RDF resource should preserve sufficient provenance to identify:

* originating source document
* source version
* source location
* generation timestamp
* generating tool version

This enables complete traceability back to the published specifications.

---

## Relationship to OTK

Semantic extraction is a core capability of the Ontology Tool Kit.

OTK is responsible for:

* parsing authoritative artifacts
* extracting semantic meaning
* minting stable IRIs
* generating RDF assets
* preserving provenance

Domain-specific projects such as UAD provide:

* source artifacts
* ontology vocabulary
* mapping policies
* validation rules

OTK provides the reusable extraction framework.

---

## Relationship to Previous ADRs

This ADR builds upon:

* ADR 0001 — Project Namespace
* ADR 0002 — IRI Minting Policy

The namespace and IRI policies govern the identities assigned to generated RDF
resources.

This ADR governs **how** those resources are created.

---

## Consequences

The project shall avoid manually recreating semantic resources that can be
deterministically generated.

Whenever practical:

* authoritative artifacts are preserved unchanged
* RDF assets are generated
* provenance is retained
* regeneration remains possible

This minimizes maintenance effort while improving consistency and traceability.

---

## References

* ADR 0001 — Project Namespace
* ADR 0002 — IRI Minting Policy
* `docs/architecture/uad36-ontology.md`
* `docs/architecture/uad-rdf-model.md`
* W3C Resource Description Framework (RDF)
* W3C Web Ontology Language (OWL)
* W3C XML Linking Language (XLink)