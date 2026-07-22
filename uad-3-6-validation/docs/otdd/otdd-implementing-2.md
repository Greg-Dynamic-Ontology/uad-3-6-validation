# Implementing OTDD - Lesson 2

## Traceability Over Ceremony

## Context

During the second OTDD implementation cycle, a new semantic competency
was selected for development involving the `SubjectProperty` class.

The intended OTDD workflow was:

1. Identify the semantic competency.
2. Create valid and invalid RDF example instances.
3. Execute the existing verification suite to confirm that no previous
   competencies have regressed.
4. Execute the new competency verification and observe a RED state.
5. Extend the ontology and SHACL shapes.
6. Execute the verification suite until GREEN.
7. Refactor while preserving competency traceability.
8. Record any lessons that improve the methodology itself.

Instead, the required SHACL constraints had already been added during
the previous implementation cycle.

## Observation

When the competency examples and verification were created, the expected
RED state did not occur.

The verification immediately passed because the implementation already
contained the required SHACL constraints.

At first this appeared to indicate a weakness in OTDD.

Further examination showed that the semantic implementation itself was
correct.

What had been lost was not correctness, but engineering traceability.
The implementation had advanced ahead of the documented semantic
competency and its verification.

## Analysis

This experience clarified an important principle.

The purpose of OTDD is **not** to enforce a sequence of ceremonial
activities.

Its purpose is to preserve engineering traceability.

The RED phase is valuable because it provides objective evidence that a
semantic competency has not yet been implemented.

When implementation precedes that evidence, the resulting ontology may
still be technically correct, but the engineering history becomes less
complete.

This lesson also highlighted the distinction between **process
discipline** and **process ceremony**.

OTDD values disciplined engineering because it preserves confidence,
repeatability, and traceability.

The process exists to support those engineering objectives—not as an end
in itself.

## Resulting Guidance

When engineering judgment and process ritual appear to conflict, OTDD
favors preserving traceability.

The recommended implementation workflow remains:

1. Identify the semantic competency.
2. Create competency examples.
3. Execute the existing verification suite.
4. Execute the new competency verification and observe RED.
5. Implement ontology and SHACL changes.
6. Execute the verification suite until GREEN.
7. Refactor while preserving competency traceability.
8. Record implementation lessons whenever the methodology itself
   evolves.

If implementation has already advanced beyond the intended workflow,
record the circumstance rather than attempting to recreate an artificial
RED state.

Engineering history should remain factual.

## Impact

### Methodology

Introduces **Traceability Over Ceremony** as a guiding principle of
OTDD.

Engineering practices exist to strengthen traceability. They are not
ceremonial requirements.

### UAD

Confirms that UAD serves as the reference implementation used to
evaluate and refine OTDD.

Experience gained while implementing UAD should improve the methodology.

### OTK

Suggests future tooling should assist engineers in maintaining
traceability between semantic competencies, examples, ontology
artifacts, verification, documentation, and measurements rather than
simply enforcing workflow steps.

### Documentation

Establishes **Traceability Over Ceremony** as a recurring design
principle for future OTDD documentation.

Future methodology changes should be justified by implementation
experience rather than theoretical preference.