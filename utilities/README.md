# Utilities

The **utilities** directory contains engineering tools used to create, extract, transform, and 
maintain artifacts used by the **UAD 3.6 Compliance** project.

Utilities are **development-time tools**. They are not part of the production validation service 
and are not required for normal operation of the API.

## Purpose

The production application validates UAD 3.6 appraisal submissions.

The utilities support the engineering activities required to build and maintain that validator, 
including:

- Extracting information from XML Schemas (XSDs)
- Generating semantic vocabularies
- Building ontology assets
- Importing reference data
- Transforming external specifications into project artifacts
- Regenerating derived assets when source specifications change

Whenever practical, generated artifacts should be reproducible by running the appropriate 
utility rather than being edited manually.

## Organization

Each utility resides in its own subdirectory.

Typical contents include:

- `README.md` — purpose and usage
- source code
- unit tests
- sample input and output files (when appropriate)

## Current Utilities

| Utility | Purpose |
|---------|---------|
| `xsd-extraction` | Extract semantic and structural information from the UAD 3.6 XML Schemas for use by downstream generators. |

## Design Principles

Utilities should:

- Perform one well-defined engineering task.
- Produce deterministic and repeatable results.
- Preserve provenance back to the authoritative source documents.
- Avoid modifying production artifacts except through documented generation processes.
- Be independently executable and testable.

The long-term objective is to automate as much of the ontology engineering workflow as practical 
while maintaining complete traceability from published GSE specifications to the generated 
semantic artifacts.