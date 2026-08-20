# Applying Isomorphism in Practice
## Query
Now that we have an understanding of graph isomorphism saved in
[meta-docs](../../docs/architecture/rdf-graph-comparison-equality-isomorphism-and-difference.md) how do we apply
that in the UAD project?
## Answer
We apply it in UAD as a **testing and reconciliation rule**, not by changing RDF into another
representation.

The first application is the namespace-correction operator:

```text
legacy Logical Schema KG
    <namespace-correction=>
canonical Logical Schema KG
```

### Which comparison UAD needs

The current Logical Schema artifact uses governed/skolemized IRIs rather than blank nodes. Therefore, its primary comparison should be **exact triple-set equality**, not graph isomorphism.

The contract is:

```text
expected-kg = independently apply ADR-0017 mapping to kg-in
observed-kg = namespace-correction operator output

observed-kg = expected-kg
```

Graph isomorphism is the fallback only when a graph deliberately contains blank nodes.

### UAD comparison policy

We should establish these rules:

| UAD situation                             | Comparison                                  |
|-------------------------------------------|---------------------------------------------|
| Repeated generation of a ground RDF graph | Exact triple-set equality                   |
| Graphs containing permitted blank nodes   | RDF graph isomorphism                       |
| Combined and Individual XSD distributions | Equivalent governed RDF output              |
| Namespace correction                      | Apply governed mapping, then exact equality |
| Operator reconciliation                   | Contract-aware comparison                   |
| Turtle files                              | Parse first; never compare serialized text  |
| Named-graph datasets                      | Dataset equality or dataset isomorphism     |

### First operator implementation

The proposed UAD structure becomes:

```text
operators/
├── __init__.py
└── namespace_correction/
    ├── __init__.py
    ├── operator.py
    ├── operator.ttl
    └── shapes.ttl
```

The operator remains simple:

```python
kg_out = namespace_correction.apply(kg_in)
```

It should:

- Return a new RDF graph.
- Replace only the ADR-0017 legacy namespace.
- Preserve the SHA-256 digest.
- Preserve every unaffected RDF term and triple.
- Leave the input graph unchanged.
- Produce deterministic, idempotent output.
- Reject malformed candidate source IRIs.

### Tests to create

The first tests should establish:

1. **Input artifact is ground**

   The canonical comparison strategy depends on there being no blank nodes.

2. **Only governed IRIs change**

   Every changed RDF term must satisfy the ADR-0017 mapping.

3. **Expected and observed graphs are equal**

```python
assert set(observed_graph) == set(expected_graph)
```

4. **No legacy IRIs remain**

5. **Every digest is preserved**

6. **Unrelated triples remain unchanged**

7. **The input graph is not mutated**

8. **The operator is idempotent**

```python
first_output = apply(input_graph)
second_output = apply(first_output)

assert set(second_output) == set(first_output)
```

9. **Serialization differences do not affect comparison**

   Both files are parsed into RDF graphs before comparison.

### Keep isomorphism explicit

We should not create a helper that silently switches to isomorphism whenever blank nodes appear. That could conceal an accidental blank node in an artifact that is required to use governed IRIs.

Prefer explicit tests:

```python
from rdflib import BNode

assert not any(
    isinstance(term, BNode)
    for triple in graph
    for term in triple
)

assert set(expected_graph) == set(observed_graph)
```

For a graph where blank nodes are intentionally allowed:

```python
from rdflib.compare import isomorphic

assert isomorphic(expected_graph, observed_graph)
```

### Reconciliation comes afterward

Once namespace correction is working, a separate reconciliation operator can consume:

```text
kg-in
+ kg-out
+ namespace-correction operator contract
```

and produce:

```text
reconciliation-kg
```

But the first UAD step should be narrower:

> Build and test the namespace-correction operator using exact RDF triple-set equality, while proving that the graphs are ground.

That turns the meta-docs understanding into a concrete UAD engineering rule without dragging the entire reconciliation architecture into the first implementation.