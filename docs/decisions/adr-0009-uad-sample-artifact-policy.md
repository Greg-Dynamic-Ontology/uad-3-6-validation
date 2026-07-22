# ADR-009: Vendor Artifact Preservation

## Status

Accepted

## Context

The UAD 3.6 Validation project incorporates vendor-supplied XML Schemas, XML instance documents, 
spreadsheets, and other reference materials as authoritative inputs.

During implementation of XML Schema validation, the published Fannie Mae example file 
`Condo1_Appraisal_v1.4.xml` failed XML Schema validation with approximately 460 errors.

Investigation determined that the failures were not caused by the project software.

Instead, many simple-content elements in the published XML examples contain formatting 
whitespace (line breaks and indentation) within values constrained by XML Schema enumerations. Removing the formatting whitespace from an individual element caused XML Schema validation to advance to the next occurrence of the same defect.

The published example files therefore cannot be used directly as validation fixtures.

This discovery illustrates an important distinction between:

* authoritative vendor artifacts
* project-generated working artifacts

These two categories have different lifecycle requirements.

---

## Decision

Vendor-supplied artifacts SHALL be preserved exactly as received.

Project developers SHALL NOT modify vendor artifacts to correct defects, formatting issues, or 
inconsistencies.

Whenever project processing requires corrected or normalized versions of vendor artifacts, 
those versions SHALL be generated automatically as derived artifacts.

The transformation process SHALL be deterministic and reproducible.

Generated artifacts SHALL never replace or overwrite the original vendor deliverables.

---

## Rationale

Preserving vendor artifacts provides:

* provenance
* repeatability
* traceability
* the ability to reproduce vendor behavior

Generating corrected copies provides:

* deterministic testing
* reproducible demonstrations
* isolation of project processing from vendor defects

This approach allows project improvements without obscuring issues present in published 
reference materials.

---

## Consequences

The repository will distinguish between:

```text
Vendor Artifacts
    specifications
    schemas
    sample XML
    spreadsheets

Derived Artifacts
    normalized XML
    RDF projections
    SHACL reports
    measurement reports
    generated vocabularies
```

Utilities may be provided to generate derived artifacts.

Those utilities are **not** part of the validation pipeline.

---

## Future Work

The project may include utilities that generate normalized copies of vendor artifacts for 
testing and demonstration purposes.

These utilities operate only on copies of vendor deliverables.

The original vendor artifacts remain immutable.

---

I would add one more paragraph because I think it captures something important that is emerging 
as a theme across your work:

> **This project distinguishes between validation of vendor artifacts and validation of 
> appraisal data. Vendor artifacts are themselves software deliverables and are therefore 
> subject to quality assessment independently of the appraisal instances they describe.**

That idea is worth emphasizing. Most projects assume schemas and sample data are infallible. 
This project is taking the position that **everything entering the pipeline is evidence**, 
including the standards artifacts themselves. 
That philosophy fits naturally with your Measurement-first approach and could become an 
important point in your Thursday publication.
