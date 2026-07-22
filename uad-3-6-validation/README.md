# UAD 3.6 Compliance (Scaffold)

FastAPI scaffold for a graph-backed UAD 3.6 validation service.

## Scope

This project validates appraisal submissions against the **UAD 3.6 XML schemas** and the 
**UAD 3.6 business rules** published by the Government-Sponsored Enterprises (GSEs).

Although UAD 3.6 is derived from MISMO 3.6, **this project does not validate documents against 
the original MISMO 3.6 XML schemas.**

### Why not validate against MISMO 3.6?

Validating a UAD 3.6 document against the original MISMO 3.6 schemas has no business value and 
can produce misleading results.

UAD 3.6 is **not validation-compatible** with the published MISMO 3.6 schemas for two 
independent reasons:

1. **UAD 3.6 is a trimmed profile of MISMO 3.6.**

   Many structures present in the MISMO 3.6 XML vocabulary are intentionally excluded from UAD 
   3.6. Consequently, an XML document may be valid according to the MISMO 3.6 schemas while 
   failing UAD 3.6 validation because it contains structures that are outside the UAD profile.

2. **UAD 3.6 incorporates later MISMO data points.**

   During development of UAD 3.6, the GSEs incorporated additional MISMO elements and attributes 
   that were introduced after the published MISMO 3.6 release. These additions remain in the 
   MISMO namespace but are not defined in the original MISMO 3.6 XML schemas. Consequently, an 
   XML document may be a valid UAD 3.6 submission while failing validation against the published 
   MISMO 3.6 schemas.

For these reasons, this project treats the UAD 3.6 schemas as the authoritative XML specification 
for validation. The original MISMO 3.6 schemas are retained only as historical and architectural 
reference material during development and are not used by the production validation pipeline.


## Run locally

```cmd
python -m venv .venv
.venv\Scripts\activate
python -m pip install -e .[dev]
uvicorn app.main:app --reload
```

## Test

```cmd
pytest
```

## Current endpoints

- `GET /health`
- `POST /ingest/schema`
- `POST /ingest/mappings`
- `POST /ingest/rules`
- `GET /resources/{resource_id}`
- `POST /validate/uad36`
- `POST /validate/uad36/fannie`
- `POST /validate/uad36/freddie`
- `GET /validation-runs/{run_id}`
- `POST /explain/finding/{finding_id}`
- `POST /review/revision-history`
- `GET /rules`
- `GET /rules/{rule_id}`
- `GET /schema/elements/{element_name}`

## Design posture

- Deterministic validators own compliance decisions.
- LLM/Ollama is advisory only.
- Every resource and finding carries provenance.
- Fannie/Freddie rule separation is explicit.
