# Architecture Decision Record 0007: Shacl Validation Without Inference
**Status:** Accepted

**Date:** 2026-07-08

## Decision

OTDD validates the explicit RDF instance graph using:
```turtle
inference="none"
```
## Rationale

Production instance documents shall explicitly declare the semantics required for validation. 
Validation should detect missing semantic assertions rather than infer them.

## Exception

Separate tests may be created to validate inference behavior when inference is itself the 
subject under test.