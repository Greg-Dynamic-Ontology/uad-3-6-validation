# RDF Graph Comparison — Equality, Isomorphism, and Difference

## Status

Private working note.

This document records the distinctions needed to compare RDF graphs and RDF
datasets. It was prompted by work on knowledge-graph operators and
reconciliation in the OWB ecosystem. It is not specific to UAD.

## The Question

When an operator transforms one knowledge graph into another, how do we decide
whether the output is correct?

Several different questions can be hidden inside the word "same":

- Do two graphs contain exactly the same triples?
- Do they differ only in their blank-node identifiers?
- Do they make the same claims under an entailment regime?
- Does one graph contain the changes required by an operator contract and no
  others?
- Do two RDF datasets contain corresponding default and named graphs?

These are different comparisons. Choosing the wrong one can make a valid graph
appear different or make an incorrect transformation appear acceptable.

## RDF Graphs Are Sets of Triples

The RDF abstract data model defines an RDF graph as a set of RDF triples. Each
triple has a subject, predicate, and object:

```text
(subject, predicate, object)
```

The triple can be visualized as a directed, predicate-labeled connection:

```text
subject ──predicate──> object
```

Because an RDF graph is a set:

- triple order has no meaning;
- serialization order has no meaning; and
- repeating the same triple does not add another assertion to the abstract
  graph.

This definition comes from the
[RDF 1.2 Concepts and Abstract Data Model](https://www.w3.org/TR/rdf12-concepts/).

## Exact RDF Graph Equality

Two RDF graphs are exactly equal when they contain exactly the same RDF
triples:

```text
G = H  when every triple in G is in H
       and every triple in H is in G
```

Equivalently:

```text
G − H = empty set
H − G = empty set
```

Graph equality is normally a definition rather than a graph-theory theorem.
The mathematically difficult question is usually graph isomorphism, where
vertex names may be changed while the structure is preserved.

Exact RDF equality is appropriate when:

- both graphs are ground graphs with no blank nodes;
- governed IRIs are expected to remain fixed;
- literals must retain their exact RDF terms; and
- the contract requires the same asserted triples.

In Python with RDFLib:

```python
equal = set(first_graph) == set(second_graph)
```

This comparison ignores Turtle formatting, prefix declarations, comments, and
triple order because those are not members of the RDF graph.

## Why an Adjacency Matrix Is Not Required

An RDF graph does not need to be converted into an adjacency matrix before it
can be compared.

An ordinary adjacency matrix is a poor natural representation for RDF because:

- RDF graphs are usually sparse;
- predicates label the directed connections;
- several predicates may connect the same subject and object;
- literals are RDF terms but normally do not act as subjects; and
- a matrix would require additional dimensions or separate matrices to retain
  predicate identity.

RDF comparison algorithms operate directly on triples or on indexes derived
from triples. An implementation may internally construct adjacency-like
indexes for efficiency, but that is an implementation choice rather than a
required change to the RDF model.

## Blank Nodes and RDF Graph Isomorphism

Blank-node identifiers are local labels used by a representation. They are not
globally governed names for resources. Two serializations can therefore use
different blank-node identifiers while representing isomorphic RDF graphs.

Consider:

```turtle
_:a ex:name "Greg" ;
    ex:address _:b .

_:b ex:city "Denver" .
```

and:

```turtle
_:person ex:name "Greg" ;
    ex:address _:location .

_:location ex:city "Denver" .
```

The graphs are isomorphic under this mapping:

```text
_:a  → _:person
_:b  → _:location
```

RDF graph isomorphism permits a consistent bijective renaming of blank nodes.
It does not permit IRIs or literals to be renamed. Predicates are IRIs and
therefore also remain fixed.

Informally, two RDF graphs are isomorphic when a one-to-one blank-node mapping
makes their triple sets equal. The formal definition is in
[RDF 1.2 Concepts, Graph Comparison](https://www.w3.org/TR/rdf12-concepts/#dfn-isomorphic).

RDFLib provides triple-based isomorphism comparison:

```python
from rdflib.compare import isomorphic

equivalent_structure = isomorphic(first_graph, second_graph)
```

No adjacency matrix is required.

## How Triple-Based Isomorphism Works

A triple-based isomorphism implementation generally:

1. treats every IRI and literal as fixed;
2. identifies the triple incident on each blank node;
3. derives structural signatures for blank nodes;
4. refines groups of possible blank-node matches;
5. resolves structurally ambiguous groups, sometimes through search or
   backtracking; and
6. it verifies that the mapped triple sets are identical.

Highly symmetric blank-node structures can be computationally expensive.
RDFLib warns that canonicalization time can grow substantially for degenerate
graphs with difficult blank-node symmetry. See the
[RDFLib graph-comparison documentation](https://rdflib.readthedocs.io/en/stable/apidocs/rdflib.compare/).

For OWB artifacts that use stable-governed IRIs instead of blank nodes, the exact
triple-set comparison is simpler and preferable.

## Canonicalization

Canonicalization assigns deterministic identifiers to blank nodes so that an
isomorphic RDF graph or dataset can receive a stable representation.

Canonicalization is useful for:

- deterministic serialization;
- graph hashing;
- digital signatures;
- repeatable graph comparison; and
- isomorphism-aware graph difference.

The W3C
[RDF Dataset Canonicalization specification](https://www.w3.org/TR/rdf-canon/)
defines an algorithm for producing stable blank-node identifiers for an RDF
dataset.

Canonicalization should not be confused with changing governed IRIs. Blank
nodes lack intrinsic global names; governed IRIs do not.

## Graph Difference

For ground graphs, a mechanical graph difference follows ordinary set
operations:

```python
first_only = set(first_graph) - set(second_graph)
second_only = set(second_graph) - set(first_graph)
in_both = set(first_graph) & set(second_graph)
```

When blank nodes are present, the graphs should be canonicalized or compared
isomorphically before calculating the difference. Otherwise, different local
blank-node labels may create false differences.

RDFLib provides an isomorphism-aware difference:

```python
from rdflib.compare import graph_diff, to_isomorphic

in_both, in_first, in_second = graph_diff(
    to_isomorphic(first_graph),
    to_isomorphic(second_graph),
)
```

The result remains a mechanical difference. It identifies common, missing,
and additional triples but does not explain whether a difference was required
by a governing transformation.

## Governed IRI Replacement Is Not RDF Isomorphism

Suppose a policy replaces this provisional IRI:

```text
https://dynamicontology.com/owb/schema-source/sha256/{digest}
```

with this governed IRI:

```text
https://dynamicontology.com/uad36/source/sha256/{digest}
```

The input and output RDF graphs are not isomorphic merely because their
structures look alike. RDF isomorphism fixes IRIs; only blank nodes may be
renamed.

The correction must instead be described by a governed transformation `f`:

```text
legacy source IRI   → governed source IRI
every other RDF term → itself
```

If `G` is the input graph, the expected graph is:

```text
E = f(G)
```

An observed output graph `H` is correct when:

```text
H = E
```

or, if blank nodes are present:

```text
H is isomorphic to E
```

The contract mapping occurs before the equality or isomorphism comparison.

## Reconciliation Is Contract-Aware Comparison

A raw graph difference does not determine whether an operator behaved
correctly. Reconciliation compares the observed output with the output
required by the operator contract.

```text
kg-in <operator=> observed-kg-out
```

The reconciliation operator consumes:

```text
kg-in + observed-kg-out + operator-contract-kg
```

and produces:

```text
reconciliation-kg
```

Conceptually:

```text
expected-kg = operator-contract(kg-in)

missing    = expected-kg − observed-kg-out
unexpected = observed-kg-out − expected-kg
```

The transformation conforms when both difference sets are empty.

The reconciliation graph is not merely a text report. It is RDF knowledge
about the comparison. It may identify:

- the input graph;
- the observed output graph;
- the operator contract;
- expected and observed transformations;
- missing statements;
- unexpected statements;
- corrected identities;
- unresolved differences; and
- conformance status.

A human-readable report may later be rendered from the reconciliation graph,
but report generation is a separate operation.

The reconciler should interpret the declarative contract independently of the
operator implementation. If it invokes the same implementation to calculate
the expected output, the same defect can occur twice and incorrectly appear
to reconcile.

## Semantic Equivalence and Entailment

Two RDF graphs can make equivalent claims without containing the same asserted
triples.

Under a specified entailment regime, graphs `G` and `H` are semantically
equivalent when:

```text
G entails H
and
H entails G
```

The entailment regime matters. Simple RDF entailment, RDF entailment, RDFS
entailment, and OWL entailment do not derive the same statements.

The
[RDF 1.2 Semantics specification](https://www.w3.org/TR/rdf12-semantics/)
defines RDF semantic interpretation and entailment. Under simple entailment,
checking a ground conclusion reduces to a triple-subset comparison. Blank
nodes make the general problem more difficult.

Semantic equivalence is appropriate when the requirement concerns meaning
rather than the exact asserted graph. It is not appropriate when an operator
contract requires preservation of particular asserted provenance,
dispositions, or source evidence.

## RDF Dataset Comparison

An RDF dataset contains:

- exactly one default graph; and
- zero or more named graphs.

Graph equality alone is insufficient when named-graph organization is part of
the requirement. Dataset comparison must also account for:

- the default graph;
- graph names;
- the graph paired with each graph name; and
- blank nodes that may be shared across graphs in the dataset.

RDF 1.2 defines dataset isomorphism using one consistent RDF-term mapping over
the default graph, named graphs, and graph names. This is important because
independently canonicalizing each named graph can lose the identity of blank
nodes shared across the dataset.

A named graph is an operational partition in an RDF dataset. The RDF data
model does not, by itself, require the graph-name IRI to denote the graph with
which it is paired. Any stronger interpretation must come from an external
contract or vocabulary.

## Choosing the Comparison

| Requirement                                              | Appropriate comparison                                       |
|----------------------------------------------------------|--------------------------------------------------------------|
| Same asserted ground RDF graph                           | Exact triple-set equality                                    |
| Same RDF graph with local blank-node labels changed      | RDF graph isomorphism                                        |
| Stable bytes, hash, or signature                         | Dataset canonicalization followed by canonical serialization |
| Same explicit triples except known additions or removals | Isomorphism-aware graph difference                           |
| Same meaning under RDFS or OWL                           | Mutual entailment under the named entailment regime          |
| Correct output from a governed graph operator            | Contract-aware reconciliation                                |
| Same default and named graphs                            | RDF dataset equality or dataset isomorphism                  |
| Same Turtle text                                         | Text comparison, which is usually not RDF graph comparison   |

## Common Comparison Errors

### Comparing Serialized Text

Two Turtle files can differ in prefixes, whitespace, ordering, and blank-node
labels while representing isomorphic RDF graphs.

### Treating IRI Renaming as Isomorphism

RDF isomorphism does not permit IRIs to be renamed. Governed IRI migration
requires an explicit mapping contract.

### Ignoring the Entailment Regime

Claims of semantic equivalence are incomplete unless they state which
entailment regime is being used.

### Comparing Named Graphs Independently

Independent graph comparison can miss blank nodes shared across an RDF
dataset or ignore a required named-graph assignment.

### Using the Production Operator as Its Own Oracle

Recomputing the expected result with the same code that produced the observed
result is not independent reconciliation.

### Comparing Literal Values Instead of RDF Terms

RDF literal equality can depend on lexical form, datatype, and language tag.
Two literals may denote the same value under a datatype interpretation while
remaining different RDF terms in an exact triple comparison.

## Testing Guidance

Tests should state the intended comparison explicitly.

For a deterministic ground graph:

```python
assert set(first_graph) == set(repeated_graph)
```

For a graph where blank-node identifiers are immaterial:

```python
from rdflib.compare import isomorphic

assert isomorphic(first_graph, repeated_graph)
```

For an operator:

```python
observed = operator.apply(kg_in)
expected = independent_contract_interpreter.apply(kg_in)

assert isomorphic(expected, observed)
```

The final example is only sound when the contract interpreter is independent
of the production operator implementation.

Ontology Test-Driven Development should also ask whether the comparison proves
the intended meaning. A passing parse test or an empty syntactic difference
does not by itself prove that the correct operator contract was selected.

## Working Conclusions

1. RDF graphs should be compared as sets of triples, not by default as text or
   adjacency matrices.
2. Exact equality is sufficient for ground graphs when governed RDF terms must
   remain fixed.
3. RDF graph isomorphism accounts only for consistent blank-node renaming.
4. Governed IRI replacement is an explicit graph transformation, not RDF
   isomorphism.
5. Graph difference is mechanical; reconciliation is contract-aware.
6. Semantic equivalence requires a declared entailment regime.
7. RDF datasets require comparison across the default graph, named graphs, and
   any shared blank nodes.
8. The comparison method is part of an operator's contract and must be chosen
   deliberately.

## Open Questions

- Which OWB graphs will permit blank nodes, and which will require governed
  IRIs?
- Should OWB adopt RDF Dataset Canonicalization for artifact digests and
  signatures?
- What vocabulary should describe operator contracts and reconciliation
  results?
- How should raw graph differences be linked to semantic reconciliation
  resources?
- Which entailment regimes are required for OWB ontology reconciliation?
- When should named-graph organization be considered part of operator output
  correctness?

## Primary References

- [RDF 1.2 Concepts and Abstract Data Model](https://www.w3.org/TR/rdf12-concepts/)
- [RDF 1.2 Semantics](https://www.w3.org/TR/rdf12-semantics/)
- [RDF Dataset Canonicalization](https://www.w3.org/TR/rdf-canon/)
- [RDFLib graph-comparison utilities](https://rdflib.readthedocs.io/en/stable/apidocs/rdflib.compare/)

