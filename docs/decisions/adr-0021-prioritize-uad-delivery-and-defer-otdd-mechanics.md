# ADR-0021: Prioritize UAD Delivery and Defer General OTDD Mechanics

**Status:** Accepted  
**Date:** 2026-11-06  
**Refines:** ADR-0006: Ontology Test-Driven Development (OTDD)

## Context

UAD has two objectives:

1. Deliver a working UAD validation application.
2. Demonstrate Ontology Test-Driven Development (OTDD) principles
   and develop practical OTDD mechanics.

Developing customer RDF persistence and SHACL validation has exposed
opportunities to explore knowledge construction, semantic testing,
and reusable OTDD tooling.

Those opportunities are valuable, but pursuing a general methodology
framework now would expand the work required before delivering UAD.

UAD delivery is the first priority. We need to preserve the OTDD
objective without making its general tooling a prerequisite for
application delivery.

## Decision

### Delivery determines the immediate work

We will implement the next required UAD acceptance scenario and its
necessary dependencies.

OTDD experiments that do not advance that scenario will be recorded
for later consideration rather than added to the immediate scope.

The current sequence is:

1. Establish the GraphDB provisioning capabilities required by UAD.
2. Complete customer RDF persistence and validation under IT-64.
3. Implement customer-account lifecycle behavior under IT-65.
4. Continue the customer validation and credit workflows.

### Apply OTDD to knowledge UAD actually needs

ADR-0006 remains in force. Deferring general tooling does not defer
verification of application knowledge.

For semantic constraints on which UAD behavior depends, we will use
representative conforming and nonconforming examples and demonstrate
the relevant RED/GREEN behavior.

We will verify that the intended constraint causes the expected
validation result. An infrastructure error does not demonstrate
a semantic RED result.

We do not require a separate RED/GREEN cycle for every vocabulary
declaration, RDF triple, or fixture file. Tests should establish
meaningful semantic behavior and protect against consequential errors.

A conforming fixture alone is insufficient evidence that a SHACL
constraint works: absent or ineffective shapes might also accept it.

### Keep responsibilities separate

- UAD owns its customer vocabulary, SHACL constraints, business rules,
  and application acceptance scenarios.
- GraphDB utilities own reusable repository provisioning,
  configuration verification, and storage operations.
- Applications supply their vocabulary, shapes, and validation scope
  to the utilities.
- OTDD process guidance and lessons are documented alongside the work.

We will not introduce UAD business rules into GraphDB utilities.

We will defer creating a separate OTDD utility package until actual
use demonstrates a stable, reusable responsibility.

### Preserve an explicit return to OTDD mechanics

During delivery work, we will record concise OTDD observations and
unresolved questions, including:

- How competencies map to vocabulary, shapes, examples, and tests.
- When knowledge construction warrants a distinct RED/GREEN cycle.
- How to demonstrate that a negative test fails for the intended reason.
- How to track shape versions and semantic test evidence.
- Which repeated operations justify reusable tooling.

At the planning review following the first working end-to-end UAD
customer validation workflow, we will explicitly revisit this backlog.

That review will decide which mechanics to develop next, whether a
separate callable package is justified, and what bounded demonstration
will validate the proposed approach.

If that work is deferred again, we will record the reason and the next
review milestone.

## Consequences

### Benefits

- UAD delivery remains the controlling priority.
- Required semantic behavior receives executable verification.
- Real application experience informs OTDD mechanics.
- GraphDB utilities remain reusable by other OWB projects.
- The intention to return to OTDD development is explicit and reviewable.

### Trade-offs

- Early semantic tests may contain some repeated setup.
- General OTDD tooling and demonstrations will arrive later.
- Lessons must be recorded while the implementation context is fresh.

We accept these trade-offs to avoid premature abstraction while
preserving UAD's role as an OTDD reference implementation.