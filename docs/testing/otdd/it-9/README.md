# IT-9 OTDD Evidence

This directory preserves experimental evidence from the first deliberate use
of Ontology-Test-Driven Development (OTDD) in the UAD 3.6 validation project.

OTDD applies the familiar red/green discipline to governed knowledge. Feature
scenarios define observable behavior, tests make that behavior executable, RDF
artifacts preserve the test inputs and expected results, and implementations
are changed only after the red state has been recorded.

## Evidence status

| Scenario                                                        | Red state                 | Green state                | Completion status                                |
|-----------------------------------------------------------------|---------------------------|----------------------------|--------------------------------------------------|
| IT-9R1S2 — Validate input and output requirements independently | Preserved                 | Preserved                  | Complete; committed and pushed as part of IT-9R1 |
| IT-9R2S1 — Correct a provisional schema-source IRI              | Preserved                 | Preserved                  | Green; IT-9R2 remains in progress                |
| IT-9R2S2 — Correct an IRI in every RDF triple position          | Preserved                 | Preserved                  | Green; IT-9R2 remains in progress                |
| IT-9R2S3 — Correct the complete Milestone 1 graph               | No red execution occurred | Preserved as initial green | Green; IT-9R2 is ready for commit and push       |

In this project, **green** means the scenario passes locally. A rule is
**complete** only after all of its scenarios are green and the rule has been
committed and pushed.

## Evidence organization

```text
docs/testing/otdd/it-9/
├── README.md
├── red/
│   ├── IT-9R1S2-input-output-validation-report.ttl
│   ├── IT-9R2S1-red-manifest.ttl
│   ├── IT-9R2S1-red-test-execution.ttl
│   ├── IT-9R2S1-test-failure.txt
│   ├── IT-9R2S1-input-graph.ttl
│   ├── IT-9R2S1-expected-output-graph.ttl
│   ├── IT-9R2S2-actual-output-graph.ttl
│   ├── IT-9R2S2-expected-output-graph.ttl
│   ├── IT-9R2S2-input-graph.ttl
│   ├── IT-9R2S2-red-manifest.ttl
│   ├── IT-9R2S2-red-test-execution.ttl
│   └── IT-9R2S2-test-failure.txt
└── green/
    ├── IT-9R1S2-input-output-validation-report.ttl
    ├── IT-9R2S1-green-manifest.ttl
    ├── IT-9R2S1-green-test-execution.ttl
    ├── IT-9R2S1-output-graph.ttl
    ├── IT-9R2S1-pytest-output.txt
    ├── IT-9R2S2-green-manifest.ttl
    ├── IT-9R2S2-green-test-execution.ttl
    ├── IT-9R2S2-output-graph.ttl
    ├── IT-9R2S2-pytest-output.txt
    ├── IT-9R2S3-initial-green-manifest.ttl
    ├── IT-9R2S3-initial-green-test-execution.ttl
    ├── IT-9R2S3-pytest-output.txt
    └── IT-9R2S3-reconciliation.ttl
```

The expected-output graph is kept with the red evidence because it is the test
oracle established before implementation. It is not evidence that an output
graph was produced during the red run.

## IT-9R1S2 — Independent conformance validation

### Purpose

IT-9R1S2 establishes that the namespace-correction input and output
requirements can be validated as governed SHACL knowledge without executing
the Python namespace-correction operator.

The acceptance test validates four controlled RDF fixtures against two SHACL
node shapes:

| Fixture                                 | Shape                             | Expected result  |
|-----------------------------------------|-----------------------------------|------------------|
| Valid provisional schema-source IRI     | Namespace Correction Input Shape  | Conforms         |
| Malformed provisional schema-source IRI | Namespace Correction Input Shape  | Does not conform |
| Valid governed schema-source IRI        | Namespace Correction Output Shape | Conforms         |
| Provisional IRI presented as output     | Namespace Correction Output Shape | Does not conform |

### Red evidence

The red test stopped before SHACL validation because the independently
executable shapes graph did not yet exist:

```text
AssertionError: IT-9R1S2 requires independent namespace-correction shapes at
operators/namespace_correction/shapes.ttl.
```

No authentic `sh:ValidationReport` was produced in that red run. The RDF file
under `red/` records that historical fact explicitly; it does not fabricate a
SHACL result.

### Green evidence

After `operators/namespace_correction/shapes.ttl` was added, all four fixture
outcomes matched their expectations and the test confirmed that SHACL
validation did not execute the Python operator implementation.

The committed green evidence contains four stable, deterministic validation
report resources. The two expected rejection reports include their SHACL
pattern violations. The two expected acceptance reports contain
`sh:conforms true` and no validation results.

## IT-9R2S1 — Correct one provisional identity

### Purpose

IT-9R2S1 requires the graph operator to replace a valid provisional
schema-source IRI with its governed UAD schema-source IRI while preserving the
64-character lowercase SHA-256 digest. The provisional IRI must not remain in
the output graph.

### Confirmed red state

The acceptance test was collected and executed. It failed at the intended
implementation boundary:

```text
FAILED tests/test_namespace_correction_operator.py::test_provisional_schema_source_iri_is_corrected - Failed: IT-9R2S1 requires the namespace-correction implementation at operators/namespace_correction/operator.py.
1 failed
```

At that point:

- `operators/namespace_correction/operator.py` did not exist;
- the namespace-correction operator did not run;
- no output RDF graph was produced;
- the input graph and expected-output graph had already been fixed as test
  evidence; and
- the exact working-tree artifacts and software versions were fingerprinted in
  `IT-9R2S1-red-manifest.ttl`.

### Red evidence inventory

- `IT-9R2S1-red-test-execution.ttl` records the failed execution and missing
  implementation as RDF.
- `IT-9R2S1-test-failure.txt` preserves the failure text reported when the
  scenario was confirmed red.
- `IT-9R2S1-input-graph.ttl` is the exact one-triple provisional input fixture.
- `IT-9R2S1-expected-output-graph.ttl` is the exact one-triple governed oracle.
- `IT-9R2S1-red-manifest.ttl` records the Git base commit, tool versions,
  implementation absence, and SHA-256 hashes of the governed and experimental
  inputs.

### Preserved green state

After `operators/namespace_correction/operator.py` was created, the focused
IT-9 tests passed:

```text
...                                                                      [100%]
3 passed in 0.49s
```

One execution of the operator consumed the preserved one-triple input graph
and produced a one-triple output graph. The actual output RDF triple set
exactly equaled the pre-implementation expected-output triple set. Their
serialized files also have the same SHA-256 hash.

### Green evidence inventory

- `IT-9R2S1-green-test-execution.ttl` records the successful test and graph
  execution as RDF.
- `IT-9R2S1-pytest-output.txt` preserves the exact focused-test result.
- `IT-9R2S1-output-graph.ttl` is the actual one-triple output produced by the
  implemented operator.
- `IT-9R2S1-green-manifest.ttl` records the implementation fingerprint,
  evidence fingerprints, environment versions, and expected-versus-actual
  equality.

## IT-9R2S2 — Correct every RDF triple position

### Purpose

IT-9R2S2 requires the same valid provisional schema-source IRI to be corrected
when it occurs as an RDF subject, predicate, or object. Each corrected term must
remain in its original triple position, and no provisional occurrence may
remain.

### Confirmed red behavior

The three-triple fixture contains one provisional occurrence in each RDF triple
position. The IT-9R2S1 implementation produced three output triples but
corrected only the object occurrence:

| Observable fact | Red-state value |
|---|---:|
| Provisional occurrences before execution | 3 |
| Provisional occurrences after execution | 2 |
| Subject occurrence corrected | No |
| Predicate occurrence corrected | No |
| Object occurrence corrected | Yes |
| Actual output exactly equals expected output | No |

After the expanded acceptance test was installed in the repository, the full
suite confirmed the intended isolated failure:

```text
1 failed, 301 passed, 1 deselected in 86.87s (0:01:26)
```

### Red evidence inventory

- `IT-9R2S2-input-graph.ttl` contains the three provisional occurrences.
- `IT-9R2S2-expected-output-graph.ttl` is the pre-implementation oracle with
  all three occurrences governed.
- `IT-9R2S2-actual-output-graph.ttl` preserves the observed partial correction.
- `IT-9R2S2-test-failure.txt` records the test result and observable graph
  facts without machine-specific paths.
- `IT-9R2S2-red-test-execution.ttl` describes the failed execution as RDF.
- `IT-9R2S2-red-manifest.ttl` fingerprints the contract, shapes, current
  implementation, installed repository test, fixture graphs, evidence, Git
  base, and software environment.

### Preserved green state

After the operator was extended to apply the same governed rewrite to every RDF
term position, the focused namespace-correction tests passed:

```text
....                                                                     [100%]
4 passed in 0.43s
```

The green execution consumed three triples, produced three triples, and left
zero provisional occurrences. The subject, predicate, and object occurrences
were all corrected without changing their positions. The actual output graph
exactly equaled the pre-implementation oracle, and their serialized files have
the same SHA-256 hash.

### Green evidence inventory

- `IT-9R2S2-output-graph.ttl` preserves the actual governed three-triple output.
- `IT-9R2S2-pytest-output.txt` preserves the focused green test result.
- `IT-9R2S2-green-test-execution.ttl` records the successful graph execution
  and positional outcomes as RDF.
- `IT-9R2S2-green-manifest.ttl` fingerprints the implemented state and records
  expected-versus-actual equality.

## IT-9R2S3 — Correct the complete Milestone 1 graph

### Initial-green status

IT-9R2S3 passed on its first executed observation. The implementation created
for IT-9R2S2 already applied the governed rewrite to every RDF triple position,
so no additional implementation change was required.

Two earlier attempts were deselected because canonical-artifact tests are
governed by the project-specific `--run-canonical-artifact` switch in
`tests/conftest.py`. Deselection is a non-execution, not a red or green test
outcome. The executed command was:

```text
python -m pytest --run-canonical-artifact tests/test_namespace_correction_complete_graph.py
```

The preserved test execution reported:

```text
.                                                                        [100%]
1 passed in 22.05s
```

### Complete-graph reconciliation

| Observable fact | Value |
|---|---:|
| Input triples | 244,023 |
| Output triples | 244,023 |
| Provisional input IRIs | 3 |
| Governed input IRIs | 0 |
| Mapped governed IRIs | 3 |
| Governed output IRIs | 3 |
| Provisional output IRIs | 0 |
| Affected input triples | 19,853 |
| Expected governed counterparts | 19,853 |
| Missing governed counterparts | 0 |
| Unexpected governed output IRIs | 0 |
| Output blank nodes | 0 |

The governed output IRI set exactly equaled the required union, and every
affected input triple had its term-for-term governed counterpart.

The complete 16 MB output graph is not duplicated in the evidence directory.
Instead, `IT-9R2S3-reconciliation.ttl` records a deterministic SHA-256 digest
of the complete sorted ground triple set, together with the hashing procedure
and reconciliation counts.

### Initial-green evidence inventory

- `IT-9R2S3-pytest-output.txt` preserves the comprehensive test result.
- `IT-9R2S3-initial-green-test-execution.ttl` records that the first execution
  was green, no red execution occurred, and no implementation change was made.
- `IT-9R2S3-reconciliation.ttl` records the complete-graph counts, reconciliation
  facts, canonical artifact hash, and output triple-set digest.
- `IT-9R2S3-initial-green-manifest.ttl` fingerprints the governed inputs,
  implementation, comprehensive-test configuration, and curated evidence.

## Red-to-green checkpoint protocol

Before an implementation is created or changed to make an OTDD scenario green:

1. Run the acceptance test and confirm that it fails for the intended reason.
2. Save the exact input graph and expected-output graph, when applicable.
3. Preserve the observed test failure without inventing unavailable execution
   details.
4. Record an RDF test-execution artifact.
5. Record a manifest containing the Git base commit, software versions, file
   hashes, and the presence or absence of the expected implementation.
6. Confirm that the red evidence is saved.
7. Issue an explicit red-evidence warning before changing implementation files.
8. Implement the smallest change required by the scenario.
9. Run the focused test and appropriate regression suite.
10. Preserve the corresponding green evidence.

## Governed source artifacts

The evidence refers to these project artifacts rather than duplicating them:

- `features/govern-schema-source-identities-in-a-knowledge-graph.feature`
- `operators/namespace_correction/operator.ttl`
- `operators/namespace_correction/shapes.ttl`
- `tests/test_namespace_correction_operator_contract.py`
- `tests/test_namespace_correction_shapes.py`
- `tests/test_namespace_correction_operator.py`
- `docs/decisions/adr-0017-IRI-and-collision-policy.md`
- `docs/decisions/adr-0018-organize-owb-as-connected-knowledge-concerns.md`

## Curated evidence versus generated reports

The files under `docs/testing/otdd/it-9/` are selected, reviewed experimental
evidence intended for version control.

Routine output under `shacl-reports/` remains reproducible working output. A
report is committed as OTDD evidence only after it is deliberately selected and
copied into this evidence package. This prevents incidental runtime files from
being mistaken for governed experimental records.
