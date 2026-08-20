# IT-9 OTDD Evidence

This directory preserves the red-to-green evidence for the first
Ontology-Test-Driven Development (OTDD) experiment in the UAD 3.6 validation
project.

## Scenario

`IT-9R1S2` — Validate input and output requirements independently.

The acceptance test validates four controlled RDF fixtures against two SHACL
node shapes:

| Fixture                                 | Shape                             | Expected result  |
|-----------------------------------------|-----------------------------------|------------------|
| Valid provisional schema-source IRI     | Namespace Correction Input Shape  | Conforms         |
| Malformed provisional schema-source IRI | Namespace Correction Input Shape  | Does not conform |
| Valid governed schema-source IRI        | Namespace Correction Output Shape | Conforms         |
| Provisional IRI presented as output     | Namespace Correction Output Shape | Does not conform |

The test also verifies that SHACL validation does not execute the Python
namespace-correction operator.

## Red evidence

The red test stopped before SHACL validation because the independently
executable shapes graph did not yet exist:

```text
AssertionError: IT-9R1S2 requires independent namespace-correction shapes at
operators/namespace_correction/shapes.ttl.
```

Consequently, the red run did not produce a `sh:ValidationReport`. The RDF file
under `red/` records that historical fact explicitly. It must not be interpreted
as a reconstructed SHACL validation result.

## Green evidence

After `operators/namespace_correction/shapes.ttl` was added, the acceptance test
passed. The RDF file under `green/` records the four fixture outcomes. It uses
stable evidence IRIs so that the committed artifact remains deterministic.

The two expected rejection reports include the SHACL pattern violations. The
two expected acceptance reports contain `sh:conforms true` and no validation
results.

## Governed inputs

- `features/govern-schema-source-identities-in-a-knowledge-graph.feature`
- `operators/namespace_correction/operator.ttl`
- `operators/namespace_correction/shapes.ttl`
- `tests/test_namespace_correction_shapes.py`
- `docs/decisions/adr-0017-IRI-and-collision-policy.md`
- `docs/decisions/adr-0018-organize-owb-as-connected-knowledge-concerns.md`

The files in this directory are curated experimental evidence. Routine SHACL
output in `shacl-reports/` remains reproducible working output and is not part of
this evidence package.
