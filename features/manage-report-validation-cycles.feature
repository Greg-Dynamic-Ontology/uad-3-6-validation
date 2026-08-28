 @IT-25
Feature: Manage UAD report-validation cycles

As a customer validating UAD appraisal reports
I want each report and its corrected submissions managed within an identifiable validation cycle
So that validation history, billable service, corrections, and passing results are unambiguous

Background:
Given the UAD report-validation service is available

  @IT-25R1
Rule: Present an explicit and honest entry experience for Demo mode

  @IT-25R1S1
Scenario: Present the initial landing-page actions
Given a visitor opens the UAD report-validation landing page
When the page finishes loading
Then the page presents "Run Validation" as the primary action
And the page presents "Documentation" as a secondary action
And selecting "Run Validation" leads to the report-validation page
And the report-validation page presents a "Validate Appraisal" action

  @IT-25R1S2
Scenario Outline: Make Demo mode visible on each service page
Given the service is operating in Demo mode
When a visitor opens the <service page>
Then a prominent "Demo Mode" indicator is visible on the page
And the indicator remains visible throughout the demo workflow
And the visitor does not have to open a dialog to discover that the service is in Demo mode

Examples:
| service page           |
| landing page           |
| report-validation page |

  @IT-25R1S3
Scenario: Explain Demo-mode limitations to an unauthenticated visitor
Given the service is operating in Demo mode
And the visitor is not logged in
When the visitor opens the landing page
Then a Demo-mode disclosure dialog is displayed
And the dialog explains that Demo mode does not provide customer-owned validation cycles
And the dialog explains that Demo mode does not retain account validation history
And the dialog explains that Demo mode does not support corrected submissions within an existing cycle
And the dialog explains that Demo mode does not purchase, hold, or consume account credits
And the dialog presents a "Cancel" action
And the dialog presents a "Continue in Demo Mode" action
And the visitor must choose one of those actions before using the "Run Validation" action

  @IT-25R1S4
Scenario: Cancel entry into Demo mode
Given an unauthenticated visitor is viewing the Demo-mode disclosure dialog
When the visitor selects "Cancel"
Then the dialog closes
And no report is uploaded
And no validation is started
And no report-validation cycle is created
And the visitor remains on the landing page

  @IT-25R1S5
Scenario: Continue with the services available in Demo mode
Given an unauthenticated visitor is viewing the Demo-mode disclosure dialog
When the visitor selects "Continue in Demo Mode"
Then the dialog closes
And the report-validation page is made available
And the "Demo Mode" indicator remains visible
And only services available under the Demo-mode policy are enabled
And continuing does not create or imply an authenticated customer account
And the visitor may select "Validate" after supplying the required demo input

   @IT-25R2
Rule: Give every new validation cycle a stable account-scoped identity

   @IT-25R2S1
Scenario: Create a pending validation cycle for a new report
Given the customer has an authenticated account
And the customer is authorized to request a new report-validation cycle
And the customer is submitting a UAD appraisal report as a new report
When the service accepts the request to begin validation
Then the service creates one pending report-validation cycle
And the service assigns a globally unique validation cycle identifier
And the validation cycle identifier is scoped to the customer's account
And the service returns the validation cycle identifier to the customer
And the submitted report is associated with the pending cycle

   @IT-25R2S2
Scenario: Keep cycle identity independent of mutable report content
Given a pending report-validation cycle exists
When the submitted report is corrected or its serialized content changes
Then the validation cycle identifier remains unchanged
And the validation cycle identifier is not derived from the report content
And the validation cycle identifier is not a GSE submission identifier
And the service does not infer cycle identity by comparing report files

   @IT-25R2S3
Scenario: Create a cycle request idempotently
Given the customer supplies an idempotency key with a request for a new validation cycle
And the request has already created a validation cycle
When the customer repeats the request with the same idempotency key
Then the service returns the existing validation cycle identifier
And no additional validation cycle is created
And no additional validation authorization is required

   @IT-25R2S4
Scenario: Prevent another customer from accessing a validation cycle
Given a validation cycle belongs to one customer account
When a different customer requests the cycle or submits a report to it
Then access is denied
And no report or validation result is disclosed
And the validation cycle remains unchanged
And the denied request is recorded for security review

   @IT-25R3
Rule: Identify submissions and control corrections within a cycle

   @IT-25R3S1
Scenario: Assign identity to every accepted report submission
Given a pending or open validation cycle exists
When the service accepts a report submission for the cycle
Then the service assigns a unique validation submission identifier
And the submission is associated with the validation cycle identifier
And the submission records its acceptance time
And the submission records an integrity digest of the submitted artifact
And the source artifact is retained or referenced according to retention policy

   @IT-25R3S2
Scenario: Accept a corrected report into its existing open cycle
Given an open validation cycle has findings
And the customer corrected the underlying data in the customer's system of record
When the customer submits the corrected report with the validation cycle identifier
Then the service associates the corrected submission with the existing cycle
And the service does not create a new validation cycle
And the corrected submission receives a new validation submission identifier
And the prior submissions and results remain in the cycle history

   @IT-25R3S3
Scenario: Require a cycle identifier for a corrected submission
Given the customer submits a report as a correction to an earlier report
When the request does not identify the existing validation cycle
Then the service does not guess which cycle owns the correction
And the correction is not attached to an existing cycle
And the customer is told to provide the validation cycle identifier

   @IT-25R3S4
Scenario: Process only one active validation attempt for a cycle at a time
Given a validation attempt is running for a validation cycle
When another submission is requested for the same cycle before the attempt completes
Then the service does not run both attempts concurrently
And the second request is rejected or held according to the service policy
And no result from the second request can supersede the active attempt before it is accepted

@IT-25R4
Rule: Produce an actionable result for every ingestible report

@IT-25R4S1
Scenario: Make a structurally invalid report an actionable validation result
Given the service can ingest the submitted artifact as a UAD appraisal report
And the report violates one or more applicable validation requirements
When validation completes
Then the service returns findings that identify what is wrong
And the result is an actionable validation result
And the result is associated with the exact validation submission

  @IT-25R5
Rule: Determine a pending cycle's outcome from its first validation attempt

  @IT-25R5S1
Scenario: Open a pending cycle when the first actionable result contains findings
Given a pending validation cycle has an accepted submission
When the service returns the cycle's first actionable validation result
And the result contains one or more validation findings
Then the pending cycle transitions to open
And the result is recorded as the cycle's current validation result
And the lifecycle records that billable validation service was delivered
And the transition is available to the credit-management capability

  @IT-25R5S2
Scenario: Close a pending cycle when the first actionable result passes
Given a pending validation cycle has an accepted submission
When the service returns the cycle's first actionable validation result
And the report passes validation
Then the pending cycle transitions directly to passed and closed
And the passing result is recorded as the cycle's current validation result
And the lifecycle records that billable validation service was delivered
And the transition is available to the credit-management capability

  @IT-25R5S3
Scenario: Cancel a pending cycle when the artifact cannot be ingested
Given a pending validation cycle has an accepted upload
When the artifact cannot be ingested as a UAD appraisal report
Then the pending cycle transitions to cancelled
And the lifecycle records that no billable validation service was delivered
And the failure reason is retained in the cycle history
And the cancellation is available to the credit-management capability

  @IT-25R5S4
Scenario: Cancel a pending cycle when the validation service fails
Given a pending validation cycle has an accepted submission
When a service failure prevents an actionable validation result
Then the pending cycle transitions to cancelled
And the lifecycle records that no billable validation service was delivered
And the failure reason is retained in the cycle history
And the cancellation is available to the credit-management capability

  @IT-25R6
Rule: Manage corrections through open and closed cycle states

  @IT-25R6S1
Scenario: Keep an open cycle open while findings remain
Given an open validation cycle receives a corrected report submission
When the actionable validation result still contains findings
Then the validation cycle remains open
And the new result becomes the cycle's current validation result
And the earlier results remain in the cycle history

  @IT-25R6S2
Scenario: Close an open cycle when a corrected report passes
Given an open validation cycle receives a corrected report submission
When the report passes validation
Then the validation cycle transitions to passed and closed
And the passing result becomes the cycle's current validation result
And all prior findings and results remain in the cycle history
And the customer is told that the report passed this validation service

  @IT-25R6S2
Scenario: Do not accept corrected submissions into a closed cycle
Given a validation cycle is passed and closed
When the customer submits another report version to the closed cycle
Then the submission is not accepted into the closed cycle
And the passing result and closed state remain unchanged
And the customer is told that another validation requires a new cycle

  @IT-25R6S3
Scenario: Create a successor cycle for later validation of a closed report
Given a report's prior validation cycle is passed and closed
And the customer is authorized to request another validation cycle
When the customer submits a later report version as a new validation cycle
Then the service creates a new pending validation cycle
And the new cycle receives a new validation cycle identifier
And the new cycle may reference the prior cycle as its predecessor
And the prior cycle remains closed and unchanged

  @IT-25R7
Rule: Apply validation-completion events exactly once and in order

  @IT-25R7S1
Scenario: Ignore a duplicate validation completion event
Given a validation result has already been recorded for a validation attempt
When the same completion event is received again
Then no duplicate result is added
And no lifecycle transition is repeated
And no additional billable-service fact is recorded
And the duplicate event is retained or logged for audit

  @IT-25R7S2
Scenario: Prevent a stale result from changing the current cycle state
Given a newer validation result has already become current for a cycle
When a delayed result from an earlier validation submission is received
Then the delayed result does not replace the current result
And the delayed result does not reopen or close the cycle
And the delayed event is retained or logged for audit

  @IT-25R8
Rule: Preserve a complete append-only validation-cycle history

  @IT-25R8S1
Scenario: Preserve an append-only cycle history
Given a validation cycle has one or more submissions, results, or state transitions
When the customer or an authorized reviewer requests the cycle history
Then the history identifies every validation submission
And the history identifies every validation attempt and result
And the history identifies every lifecycle state transition
And each recorded event identifies its effective time
And prior history is not overwritten by later submissions or results

  @IT-25R9
Rule: Keep validation separate from the customer's system of record and GSE submission

  @IT-25R9S1
Scenario: Keep validation separate from the customer's system of record and GSE submission
Given a report passes a report-validation cycle
When the service returns the passing result
Then the service does not modify the customer's system of record
And the service does not replace the customer's authoritative report
And the service does not submit the report to a GSE
And the customer remains responsible for GSE submission
