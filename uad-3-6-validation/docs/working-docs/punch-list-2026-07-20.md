# Morning Punch List — Process Input Files

## Starting State

- Test suite is green: **157 passed**
- No functional code has changed since the last commit
- ADR 0008 is drafted but is not part of this morning's implementation work
- The canonical internal representation decision is settled:
  - Most meaningful input is transformed into RDF+/OWL
  - All meaningful output is derived from RDF+/OWL
  - Intermediate engineering representations are permitted but are not authoritative

---

## Morning Objective

Accept an XML instance through the site, process it through the existing validation service, 
and establish the resulting validation facts in the canonical RDF+/OWL representation.

Do not add SHACL validation, measurements, or report styling during this work block.

---

## 1. Review the Existing Site Entry Point

Identify:

- the application entry point
- the existing route definitions
- the current page structure
- any existing upload form or request handler
- where application services are currently invoked

Do not change code during this review.

---

## 2. Review the Current Validation Service

Confirm the existing public interface for XML Schema validation.

Determine:

- what input form the validator currently accepts
- what intermediate result it returns
- which parts of that result must be projected into RDF+/OWL
- whether any existing RDF vocabulary already represents validation runs, findings, status, or source documents

Do not redesign the validator unless the site integration reveals a real boundary problem.

---

## 3. Define the Input-Processing Boundary

The web layer is responsible for:

- accepting the submitted XML representation
- passing the XML content to the application service
- requesting a derived site response

The web layer is not responsible for:

- XML Schema validation logic
- RDF construction rules
- semantic interpretation
- report facts
- business-rule evaluation

The application-processing flow is:

```text
Submitted XML representation
        ↓
Input-processing service
        ↓
XML Schema validation machinery
        ↓
Intermediate engineering result
        ↓
Validation facts projected into RDF+/OWL
        ↓
Site output derived from RDF+/OWL
```

The upload transport mechanism may use memory, streaming, or framework-managed temporary storage. That is an implementation detail and is not an architectural stage.

---

## 4. Write the First Test Before Implementation

Create the first integration test for submitted XML processing.

The test should prove that:

1. a valid XML instance can be submitted through the application boundary
2. the existing XML Schema validator is invoked
3. the resulting validation facts are represented in RDF+/OWL
4. the canonical graph contains the expected validation status
5. the request completes without embedding validation logic in the web layer

The test should inspect the canonical RDF+/OWL result, not merely a Python object or JSON payload.

Run the focused test and confirm that it fails for the expected missing implementation.

---

## 5. Implement the Minimum Processing Path

Implement only enough code to satisfy the first test.

Expected responsibilities:

- receive the submitted XML content
- invoke the existing validation service
- project the validation result into RDF+/OWL
- derive the initial site response from the canonical graph

Avoid:

- SHACL validation
- measurement generation
- inference
- visual styling
- generalized plugin architecture
- speculative support for additional input formats
- duplicate report models that could become an alternative source of truth

---

## 6. Add the Invalid-Input Case

After the valid-input test is green, add a second test proving that an invalid XML instance:

- is processed without an unhandled exception
- produces RDF+/OWL validation findings
- records a failing validation status
- preserves available source locations and diagnostic details
- produces a site response derived from those graph facts

Return the focused tests to green.

---

## 7. Run the Full Test Suite

Run:

```cmd
python -m pytest
```

Confirm that:

- all existing 157 tests still pass
- all new tests pass
- no unrelated regressions were introduced

---

## Morning Stop Point

Stop when the following statement is true:

> The site accepts an XML instance, invokes the existing XML Schema validation service, represents the validation result canonically in RDF+/OWL, and derives its response from that canonical representation.

Anything beyond that statement belongs to the next work block.
