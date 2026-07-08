# UAD 3.6 Compliance (Scaffold)

FastAPI scaffold for a graph-backed UAD 3.6 validation service.

This is intentionally an MVP skeleton. It provides API contracts, in-memory adapters, models, and tests 
aligned to the initial BDD feature file. GraphDB, SHACL/SPARQL execution, real GSE schema ingestion, 
Appendix A mappings, Appendix H rules, and Ollama-backed review are represented by replaceable 
service-adaptor boundaries.

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
