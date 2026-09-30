# IT-1R2S1 single-equality completion

Date: 2026-09-29. Scope: all 174 governed single-equality rules.

## Changes

The 136 previously unbound rules now have executable RDF cases.
They comprise 76 same-container conditions, 38 comparable-property
attribute conditions, and 22 cross-container conditions.
UAD1022 already had production support; the other 135 rules are
implemented through `data/single-equality-bindings.ttl` and
`app/services/single_equality_required_data.py`.
Production reads no test fixtures or expected results.
Each production binding pins the governed CSV row using SHA-256
over identity, logic, element, severity, property scope, path, and
message.

The evaluator keeps triggers within the same property, report,
party, structure, or utility occurrence. For party names, a role
held by that same party controls the requirement.
Attribute triggers apply only to the specified comparable type.
Absent/blank/nil trigger values do not satisfy equality.
Missing dependent containers are handled for applicable
non-instance requirements; source wording that says "in a given
instance" limits evaluation to existing instances.

## Fixtures and source preservation

136 synthetic baseline XML fixtures are stored under
`data/uad36-test-suite/tests/fixtures/single_equality/derived/`.
`provenance.json` records the published baseline and SHA-256,
derived-file hash, trigger and dependent paths, and each changed
XML node.
These are test inputs, not claims of authentic appraisals or
complete compliance.
Required schema containers were added where necessary.
All baselines and the three original behavior variants pass the
published XSD.
All referenced published sample hashes were verified unchanged.
Published sources were not edited.

## RED and GREEN evidence

- Before production implementation: **135 failed, 387 passed**.
Every failure was a matching-missing case expecting one finding
and receiving zero.
There were no collection or setup errors.
Already-supported UAD1022 was green.
- After implementation: **522 passed** across all 174 rules.
- Scope and missing-value checks: **419 passed**
(408 empty/whitespace/nil checks, seven cross-occurrence checks,
four missing-container checks).
Empty numeric/date values deliberately exercise the required-data
layer; they are not described as schema-valid.
Nil variants are schema-validated.
- Legacy unconditional fixtures and the SHACL count contract:
**108 passed**.
- Expanded full-suite result, including normally deselected
canonical checks: **2 failed, 2,064 passed in 419.18 seconds**.
- All standard acceptance tests passed.
The two failures are listed below; the full suite is not wholly
green.

## Unresolved canonical-artifact checks (outside IT-1R2)

1. `tests/test_logical_schema_graph_is_generated.py::test_complete_uad_graph_matches_canonical_artifact`:
   the saved Logical Schema graph is stale: 19,819 generated
triples are absent and 19,819 saved triples are not produced by
the current model.
2. `tests/test_namespace_correction_complete_graph.py::test_complete_logical_schema_graph_is_namespace_corrected`:
   the test requires provisional schema-source IRIs in the saved input graph,
   but that graph has none.

These are the two checks normally deselected by `tests/conftest.py`.
Neither those tests, their generator/operator, nor the canonical
graph was changed in this task.
Repairing the canonical snapshot and deciding which input the
namespace transformation test should use remains separate work.

Two legacy setup assertions incorrectly required Unique IDs to
identify rules uniquely.
They now assert Message ID uniqueness; all unconditional fixture
coverage and finding expectations are unchanged.
The source has shared/blank Unique IDs, which remain preserved.
The runner also accepts the source's uppercase "IF" spelling for
UAD1195 without altering its condition or expected result.

No unresolved source ambiguity was found in this slice.
`PROJECT_CONVERSION` uses schema type `CONVERSION`;
this is a schema alias, not a source defect.
The other rule categories and broader sufficient scenarios
remain outside this completion claim.
No commit or push was performed.

## Reproduce

```bat
.\.venv\Scripts\python.exe -B -m pytest tests/test_it_1_r2_single_equality_behavior.py tests/test_single_equality_scope_integrity.py tests/test_it_1_r2_case_count.py -q --tb=short -p no:cacheprovider
.\.venv\Scripts\python.exe -B -m pytest tests data/uad36-test-suite/tests/test_required_data_acceptance.py data/uad36-test-suite/tests/test_required_data_rdf.py --run-canonical-artifact -q --tb=short -p no:cacheprovider
```

## Artifact fingerprints

- `data/data-constraints.csv`: `82e96099950a7e4e1d5a1176e12246f3b41425b3c5489eea5b822b81033246dc`
- `data/single-equality-bindings.ttl`: `66f595b3e42fd391919fc2283a0170d2907742fae60d97dae15c9d812d1d0c96`
- `data/uad36-test-suite/tests/fixtures/single_equality/test-suite.ttl`: `52f365147a73b827bf6e15849f1696b16d6595544cc8ff8d26a9833400dc3b8b`
