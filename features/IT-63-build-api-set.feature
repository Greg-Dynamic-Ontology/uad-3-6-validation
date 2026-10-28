# Derived from the project README's scope, current endpoints, and design posture.
# This feature describes observable API behavior; local installation and launch
# instructions remain in the README. Existing endpoint implementations may already
# satisfy individual scenarios.

@IT-63
Feature: Build the UAD validation API set
  As a client of the UAD validation service
  I want APIs for governed knowledge ingestion, appraisal validation, and result inspection
  So that I can validate UAD 3.6 submissions and retrieve traceable compliance results

  Background:
    Given the UAD validation service is available through its FastAPI application
    And the service uses a graph-backed knowledge store
    And the UAD 3.6 XML schemas are the authoritative schemas for appraisal validation
    And governed GSE business rules are available with explicit investor applicability

  @IT-63R1
  Rule: The API exposes service health

        @IT-63R1S1
    Scenario: Check service health
      When the client requests GET "/health"
      Then the API returns a successful health response
      And the response identifies the service health state

        @IT-63R1S2
    Scenario: Check health through the running API server
      Given the UAD API server is expected at "http://localhost:4000"
      When the client sends an HTTP GET request to "http://localhost:4000/health"
      Then the running server returns HTTP 200
      And the response is JSON
      And the response identifies the service health state as "ok"
      And the request uses an actual network connection rather than an in-process test client

  @IT-63R2
  Rule: The API gatekeeper accepts or rejects proposed schema candidates

        @IT-63R2S1
    Scenario: Reject malformed XML at the schema ingestion gatekeeper
      Given the UAD API server is running at "http://localhost:4000"
      And the proposed schema contains malformed XML
      And source provenance accompanies the submission
      When the client submits the proposed schema to POST "http://localhost:4000/ingest/schema" over an actual network connection
      Then the API returns HTTP 400
      And the diagnostic identifies malformed XML as the rejection reason
      And the submission is not recorded as an accepted schema candidate
      And no further schema analysis is started

        @IT-63R2S2
    Scenario Outline: Reject an incorrect schema root name or namespace
      Given the UAD API server is running at "http://localhost:4000"
      And the proposed schema is well-formed XML
      And its document element has local name "<root_name>"
      And its document element has namespace "<namespace>"
      And source provenance accompanies the submission
      When the client submits the proposed schema to POST "http://localhost:4000/ingest/schema" over an actual network connection
      Then the API returns HTTP 400
      And the diagnostic identifies the expected root as "{http://www.w3.org/2001/XMLSchema}schema"
      And the diagnostic identifies the submitted root name and namespace
      And the submission is not recorded as an accepted schema candidate
      And no further schema analysis is started

      Examples:
        | root_name | namespace                            |
        | document  | http://www.w3.org/2001/XMLSchema      |
        | Schema    | http://www.w3.org/2001/XMLSchema      |
        | schema    | urn:example:other                    |
        | schema    |                                      |

        @IT-63R2S3
    Scenario: Accept an XML Schema candidate through the running API gatekeeper
      Given the UAD API server is running at "http://localhost:4000"
      And the proposed schema is well-formed XML
      And its document element has local name "schema"
      And its document element has namespace "http://www.w3.org/2001/XMLSchema"
      And source provenance accompanies the submission
      When the client submits the proposed schema to POST "http://localhost:4000/ingest/schema" over an actual network connection
      Then the API accepts the submission for further analysis
      And the response identifies the recorded schema candidate
      And the recorded candidate preserves the submitted content and its content digest
      And the recorded candidate preserves its source provenance
      And acceptance is independent of the XML namespace prefix used
      And acceptance permits schema documents containing only imports or includes
      And acceptance does not require resolving referenced schema documents
      And acceptance does not certify schema correctness or completed component analysis

  @IT-63R3
  Rule: Governed schemas, mappings, and rules can be ingested and retrieved

    @IT-63R3S1
    Scenario: Ingest an XML Schema artifact
      Given a supported XML Schema artifact with source provenance
      When the client submits the artifact to POST "/ingest/schema"
      Then the API records a schema resource in the knowledge store
      And the resource has an identity usable for subsequent retrieval
      And the resource retains its source provenance
      And schema ingestion does not require the artifact to belong to UAD 3.6

    @IT-63R3S2
    Scenario: Ingest mapping knowledge
      Given supported mapping knowledge with source provenance
      When the client submits the knowledge to POST "/ingest/mappings"
      Then the API records mapping resources in the knowledge store
      And the recorded resources have identities usable for subsequent retrieval
      And the resources retain their source provenance

    @IT-63R3S3
    Scenario: Ingest governed business rules
      Given supported UAD business-rule knowledge with source provenance
      And each rule identifies its governed GSE applicability
      When the client submits the knowledge to POST "/ingest/rules"
      Then the API records governed rule resources in the knowledge store
      And each rule retains its governed identity and source provenance
      And each rule retains its explicit GSE applicability

    @IT-63R3S4
    Scenario: Retrieve a stored resource by identity
      Given an ingested resource has a resource identifier
      When the client requests GET "/resources/{resource_id}" with that identifier
      Then the API returns the identified resource
      And the response preserves its identity and provenance

  @IT-63R4
  Rule: Appraisal validation applies UAD schemas and explicitly scoped GSE business rules

    @IT-63R4S1
    Scenario: Validate an appraisal through the general validation endpoint
      Given an appraisal submission and its requested investor scope
      When the client submits the validation request to POST "/validate/uad36"
      Then the service evaluates the appraisal against the UAD 3.6 schemas
      And the service evaluates business rules applicable to the requested investor scope
      And the API returns an identified validation run and its results
      And the run records the investor scope and governed knowledge used

    @IT-63R4S2
    Scenario Outline: Validate an appraisal for one named GSE
      Given an appraisal submission
      And governed business rules distinguish Fannie Mae and Freddie Mac applicability
      When the client submits the appraisal to POST "<endpoint>"
      Then the service evaluates the appraisal against the UAD 3.6 schemas
      And the business-rule evaluation uses the <investor> scope
      And rules exclusive to the other investor are not applied
      And rules applicable to the selected investor remain eligible for evaluation
      And the returned validation run records the selected investor scope

      Examples:
        | endpoint                   | investor    |
        | /validate/uad36/fannie      | Fannie Mae  |
        | /validate/uad36/freddie     | Freddie Mac |

    @IT-63R4S3
    Scenario: Reject structures outside the UAD schema profile
      Given an appraisal XML document contains a structure permitted by original MISMO 3.6
      And the authoritative UAD 3.6 schemas do not permit that structure in its submitted context
      When the client submits the document to POST "/validate/uad36"
      Then the result reports the UAD schema violation
      And compatibility with original MISMO 3.6 does not override that result

    @IT-63R4S4
    Scenario: Accept UAD schema additions without requiring original MISMO schema compatibility
      Given an appraisal XML document conforms to the authoritative UAD 3.6 schemas
      And the document uses a permitted UAD data point absent from original MISMO 3.6
      When the client submits the document to POST "/validate/uad36"
      Then the schema-validation result is conforming
      And the absence of that data point from original MISMO 3.6 is not reported as a violation
      And governed business-rule results remain independently determined

  @IT-63R5
  Rule: Validation runs and findings retain retrievable identities and provenance

    @IT-63R5S1
    Scenario: Retrieve a recorded validation run
      Given an appraisal validation run has been recorded with a run identifier
      When the client requests GET "/validation-runs/{run_id}" with that identifier
      Then the API returns the identified run and its recorded results
      And the run remains traceable to the appraisal submission
      And the run remains traceable to the governed schema and business-rule knowledge used

    @IT-63R5S2
    Scenario: Preserve the governed identity and provenance of a finding
      Given appraisal validation produces a governed business-rule finding
      When the API returns the finding as part of the validation result
      Then the finding identifies its governed rule
      And the finding remains traceable to its validation run and governed source knowledge
      And the finding retains its investor applicability

  @IT-63R6
  Rule: Clients can inspect governed rules, schema elements, and revision history

    @IT-63R6S1
    Scenario: List available governed rules
      Given governed rules are recorded in the knowledge store
      When the client requests GET "/rules"
      Then the API returns the available governed rules
      And each listed rule identifies its governed identity and GSE applicability

    @IT-63R6S2
    Scenario: Inspect one governed rule
      Given a governed rule has a rule identifier
      When the client requests GET "/rules/{rule_id}" with that identifier
      Then the API returns the identified rule
      And the response retains the rule's governed meaning, provenance, and GSE applicability

    @IT-63R6S3
    Scenario: Inspect a UAD schema element
      Given a named UAD schema element is represented in the knowledge store
      When the client requests GET "/schema/elements/{element_name}" with that name
      Then the API returns schema knowledge for that element
      And the response retains its governed schema identity and source provenance

    @IT-63R6S4
    Scenario: Review revision history
      Given recorded revision history is available for a governed resource
      When the client submits a review request to POST "/review/revision-history"
      Then the API returns the revision history for the requested resource
      And the returned revisions remain traceable to that resource and their provenance

  @IT-63R7
  Rule: Deterministic validators own compliance decisions and generated explanations remain advisory

    @IT-63R7S1
    Scenario: Explain a recorded finding without changing the compliance decision
      Given a finding has been produced by deterministic validation
      And the finding has a finding identifier
      When the client requests an explanation through POST "/explain/finding/{finding_id}"
      Then the API returns an advisory explanation associated with that finding
      And the explanation does not change the recorded validation decision
      And the explanation does not change the finding's governed identity, meaning, or severity

    @IT-63R7S2
    Scenario: Keep compliance results independent of advisory model output
      Given an appraisal submission and fixed governed validation knowledge
      When the same appraisal is validated with different advisory model responses
      Then the deterministic compliance decisions remain the same
      And the governed findings remain the same apart from execution-specific identity and provenance
      And advisory model output does not create or suppress compliance findings
