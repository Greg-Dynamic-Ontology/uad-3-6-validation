Feature: Return auditable validation results through an API

As an API consumer
I want machine-readable and reviewer-readable validation results
So that findings can be corrected, explained, stored, and audited

Background:
Given a UAD 3.6 appraisal report package has been validated

Scenario: Return a structured validation response
When validation is complete
Then the API response includes a validation run identifier
And the API response includes the UAD version
And the API response includes the rule set versions applied
And the API response includes a summary count by severity
And the API response includes all findings

Scenario: Return auditable finding details
Given a validation finding exists
When the finding is returned
Then the finding includes a finding identifier
And the finding includes severity
And the finding includes the affected XML location
And the finding includes the affected graph resource IRI
And the finding includes the governing rule identifier
And the finding includes the source specification reference
And the finding includes the observed value when applicable
And the finding includes the expected condition when applicable

Scenario: Explain a finding
Given a validation finding exists
When the client requests an explanation for the finding
Then the service returns a plain-language explanation
And the explanation cites the governing rule or specification source
And the explanation does not replace the authoritative validation result

Scenario: Review freeform revision history detail
Given a UAD 3.6 appraisal report package contains Revision History Detail text
When the client requests freeform revision-history review
Then the service evaluates the text for likely responsiveness to reported findings
And the service returns reviewer-assistance comments
And the service marks the comments as advisory
And the service does not treat advisory comments as deterministic validation failures

Scenario: Query rules through the API
When the client requests the available UAD 3.6 rules
Then the service returns rule identifiers
And each rule identifies its source
And each rule identifies whether it applies to Fannie Mae, Freddie Mac, or both
And each rule identifies its current version status
