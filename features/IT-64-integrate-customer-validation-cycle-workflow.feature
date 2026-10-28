# Integration requirements for existing report-validation lifecycle behavior.
# IT-25 remains authoritative for cycle identity, submissions, transitions,
# history, billable-service facts, and the customer/GSE service boundary.
# IT-2 governs authentication and local user linkage; IT-44 governs customer
# accounts, membership, authorization, and operating-mode policy.
# IT-45 governs credit policy; this feature connects the existing credit
# capability without introducing payment-provider or purchasing workflows.
# IT-46 governs validation coverage and upload-to-report behavior. A corrected
# upload creates a new validation run while retaining its existing open cycle.
# These integration scenarios supplement rather than replace existing tests.
# Integration evidence uses the running application, real HTTP requests,
# configured durable repositories, and the production validation engine.
# Browser scenarios use browser actions, not direct lifecycle service calls.
# Controlled infrastructure failures may be injected at the tested boundary;
# successful validation and persistence are not replaced with canned results.

@IT-64
Feature: Integrate the customer report-validation cycle workflow
  As an authenticated UAD customer
  I want the browser and API to manage report validation through durable account-owned cycles
  So that my submissions, corrections, results, and history remain consistent and retrievable

  Background:
    Given the UAD application is running at its configured HTTP address
    And the existing sign-in and local-user linkage capability is available
    And customer accounts, memberships, and permissions are governed by IT-44
    And the application connects its API to the existing IT-25 lifecycle services
    And configured durable storage retains cycles, submissions, attempts, results, and history
    And source artifacts are retained or referenced according to the configured retention policy
    And the production validation engine has an identified governed schema and selected constraint-set coverage
    And required new-cycle authorization is supplied by the existing authorization and credit capabilities

  @IT-64R1
  Rule: Browser access reflects verified identity, account membership, and operating-mode policy

    # Integrates IT-2R5/R6, IT-25R1, and IT-44R3/R6/R9.
    @IT-64R1S1
    Scenario: Reach the account validation page after successful sign-in
      Given a user has a linked UAD identity and an active customer-account membership
      And that membership permits report validation
      And the operating-mode policy permits account-owned validation
      When the user signs in through the existing browser sign-in flow
      And opens report validation for that customer account
      Then the browser identifies the verified user and selected customer account
      And the page offers a new report-validation cycle
      And the displayed operating mode reflects the governed account policy
      And a hard-coded Demo indicator does not override the resolved operating mode
      And sign-in alone does not create a validation cycle

    @IT-64R1S2
    Scenario: Preserve Demo entry behavior for a Demo visitor
      Given the visitor is operating under the Demo-mode policy
      When the visitor opens the landing page and continues into report validation
      Then the disclosure, cancellation, continuation, and visible Demo indicators follow IT-25R1
      And continuing in Demo mode does not create an authenticated customer account
      And Demo requests do not create customer-owned cycles or consume account credits

    @IT-64R1S3
    Scenario: Require sign-in before creating an account-owned cycle
      Given the visitor has no valid authenticated session
      When the visitor requests creation of an account-owned cycle through the browser
      Then the application requires the existing sign-in flow
      And no account-owned cycle or report submission is created by that request
      And no customer validation history is disclosed

    @IT-64R1S4
    Scenario: Reject a cycle request without account authorization
      Given a signed-in user lacks validation permission in the requested customer account
      When the user submits a new-cycle request directly to the API
      Then the API denies the request
      And no cycle, submission, validation attempt, or credit debit is created
      And client-supplied user or account identifiers do not replace verified authorization

  @IT-64R2
  Rule: A new report request connects account authorization, lifecycle creation, and actual validation

    # Integrates IT-25R2, IT-25R3S1, IT-25R4, IT-25R5S1/S2, and IT-46.
    @IT-64R2S1
    Scenario: Submit a report and inspect its first actionable result through the browser
      Given a signed-in customer is authorized to open a new validation cycle
      And a controlled ingestible report produces a known governed validation finding
      When the customer uploads the report and requests a new cycle in the browser
      Then the browser submits the request to the running application API
      And one pending account-owned cycle is recorded by the lifecycle services
      And an accepted submission records its own identity, acceptance time, and artifact digest
      And a validation attempt executes the production validation engine against that submission
      And the first actionable result identifies the cycle, submission, attempt, and validation run
      And the cycle transitions to open
      And the browser displays the expected governed finding and affected XML context
      And the result identifies the governed schema and constraint-set versions used
      And the billable-service lifecycle fact is available to credit management
      And the uploaded report remains unchanged

    @IT-64R2S2
    Scenario: Close a new cycle when the first actionable result passes
      Given a signed-in customer is authorized to open a new validation cycle
      And a controlled report passes the selected governed validation coverage
      When the customer submits the report as a new cycle through the API
      Then the production engine evaluates the accepted submission
      And the lifecycle records the passing result for that exact submission
      And the pending cycle transitions directly to passed and closed
      And the browser can retrieve and display the passing result
      And the result states the coverage actually evaluated
      And the billable-service lifecycle fact is available to credit management

    @IT-64R2S3
    Scenario: Reuse a cycle when a new-cycle request is retried
      Given a customer's new-cycle request has been accepted with an idempotency key
      When the customer repeats the same request with the same account-scoped key
      Then the API returns the original cycle identity and its recorded request outcome
      And no duplicate cycle, submission, or validation attempt is created
      And new-cycle authorization and billable-service recording are not repeated

  @IT-64R3
  Rule: Committed lifecycle knowledge survives restart and remains consistent across failures

    # Integrates durable adapters for IT-25 repository contracts.
    @IT-64R3S1
    Scenario: Retrieve a cycle and its history after restarting the application
      Given a customer has submitted a report and received a recorded validation result
      And the cycle, submission, attempt, result, and history have been committed to storage
      When the application is stopped and restarted using the same configured storage
      And the customer signs in and requests the cycle through the API and browser
      Then the cycle retains its original identity, owner, state, and current result
      And the submission and attempt retain their original identities and provenance
      And the artifact digest and retained artifact reference remain available
      And the recorded findings and history remain retrievable
      And retrieval does not rerun validation or record another billable-service fact

    @IT-64R3S2
    Scenario: Recover an accepted request after its response is lost
      Given a new-cycle request was durably committed with its idempotency key
      And the client did not receive the response
      When the application restarts and the customer retries with the same key
      Then the API resolves the committed request to the original cycle
      And recorded submissions, attempts, results, and history are reused
      And a completed validation is not executed again because its response was lost

    @IT-64R3S3
    Scenario: Roll back an incomplete lifecycle storage operation
      Given an account-authorized lifecycle operation requires related storage changes
      And a controlled storage failure occurs before that operation commits
      When the application handles the failure
      Then the API reports that the requested operation did not complete
      And the related lifecycle changes are not partially committed
      And no successful lifecycle outcome or billable-service fact is exposed for the failed commit
      And a retry can proceed from the last committed state

  @IT-64R4
  Rule: Corrected submissions retain their cycle and preserve earlier results

    # Integrates IT-25R2S2, IT-25R3S2/S3, and IT-25R6S1/S2.
    @IT-64R4S1
    Scenario: Submit a correction while findings remain
      Given an account-owned open cycle has a recorded result with findings
      And the customer prepares a corrected report that still has a known governed violation
      When the customer submits the correction from that cycle's browser page
      Then the request explicitly identifies the existing cycle
      And the lifecycle records a new submission and attempt within that same cycle
      And the validation engine evaluates the new submission
      And the cycle remains open with the new result current
      And the browser shows the new result alongside retrievable earlier history
      And the changed artifact content does not change the cycle identity

    @IT-64R4S2
    Scenario: Close an open cycle after a passing correction
      Given an account-owned open cycle has a recorded result with findings
      And the customer corrects the report so that it passes the selected validation coverage
      When the customer submits the corrected report with that cycle identifier
      Then a new submission, attempt, and validation run are recorded in the existing cycle
      And the engine's passing result becomes current
      And the lifecycle transitions the cycle to passed and closed
      And the browser tells the customer that the report passed this validation service
      And all earlier submissions, findings, and results remain in history

    @IT-64R4S3
    Scenario: Reject a correction that omits its cycle identifier
      Given a customer requests validation as a correction to an earlier report
      When the API receives the correction without a cycle identifier
      Then the API rejects the correction with an actionable diagnostic
      And the browser tells the customer to identify the existing cycle
      And report content or filenames are not used to guess cycle ownership
      And no submission, attempt, or new cycle is created for the rejected correction

  @IT-64R5
  Rule: Closed cycles remain closed and later validation uses a new cycle

    # Integrates IT-25R6S3/S4.
    @IT-64R5S1
    Scenario: Reject a correction directed to a closed cycle
      Given a customer's cycle is passed and closed
      When the customer submits another version as a correction to that cycle
      Then the API rejects the correction and the browser explains that a new cycle is required
      And the passing result, closed state, and existing history remain unchanged

    @IT-64R5S2
    Scenario: Start an authorized successor cycle for a later report version
      Given a customer's earlier cycle is passed and closed
      And the customer is authorized to request another cycle
      When the customer submits a later report version as a new cycle
      Then the lifecycle creates a new pending cycle with a new identity
      And the new cycle may reference the earlier cycle as its predecessor
      And the previous cycle remains closed with its original passing result

  @IT-64R6
  Rule: The integrated workflow distinguishes actionable findings from processing failures

    # Integrates IT-25R4S1, IT-25R5S3/S4, and IT-46 failure reporting.
    @IT-64R6S1
    Scenario: Return actionable findings for an ingestible structurally invalid report
      Given an authorized pending cycle has an accepted report artifact
      And the artifact is ingestible as a UAD appraisal report
      And it violates a governed structural validation requirement
      When the validation engine completes its assessment
      Then the API records an actionable result associated with the exact submission and attempt
      And the cycle becomes open
      And the browser displays the governed structural findings
      And the artifact is not treated as unprocessable solely because validation found structural errors

    @IT-64R6S2
    Scenario: Cancel a pending cycle for an unprocessable upload
      Given a pending cycle has an accepted upload
      And the upload cannot be ingested as a UAD appraisal report
      When the application processes the upload
      Then the lifecycle cancels the pending cycle with the failure reason retained
      And the API and browser explain why the upload could not be processed
      And no passing or actionable validation result is fabricated
      And the lifecycle records that no billable validation service was delivered
      And the cancellation is available to credit management

    @IT-64R6S3
    Scenario: Cancel a pending cycle when validation execution fails
      Given a pending cycle has an accepted submission
      And a controlled execution failure prevents an actionable validation result
      When the application handles the failed validation attempt
      Then the lifecycle cancels the pending cycle and retains the execution failure reason
      And the browser displays an unsuccessful outcome with any partial results marked incomplete
      And unevaluated checks are not reported as passing
      And the lifecycle records that no billable validation service was delivered
      And the cancellation is available to credit management

  @IT-64R7
  Rule: Concurrent requests and completion events preserve one authoritative lifecycle outcome

    # Integrates IT-25R3S4 and IT-25R7; assertions include durable state.
    @IT-64R7S1
    Scenario: Prevent concurrent validation attempts for one cycle
      Given a validation attempt is running for an account-owned cycle
      When another submission request reaches the API for that cycle
      Then the second request is rejected or held according to the governed service policy
      And two validation attempts do not execute concurrently for that cycle
      And a browser retry cannot bypass the active-attempt guard

    @IT-64R7S2
    Scenario: Apply a repeated completion event once across application restart
      Given a validation-completion event has already been committed for an attempt
      When the application restarts and receives the same completion event again
      Then the existing lifecycle service identifies the event as a duplicate
      And no duplicate result, transition, or billable-service fact is recorded
      And the duplicate event is retained or logged for audit
      And the API and browser continue to show the same authoritative result

    @IT-64R7S3
    Scenario: Preserve the current result when an older completion arrives late
      Given a newer submission's result is current for a cycle
      When a delayed completion for an earlier submission reaches the application
      Then the earlier result does not replace the current result or change the cycle state
      And the delayed event is retained or logged for audit
      And the browser continues to identify the newer submission's result as current

  @IT-64R8
  Rule: Account-scoped retrieval exposes complete append-only history

    # Integrates IT-25R2S4 and IT-25R8, with IT-44 permissions.
    @IT-64R8S1
    Scenario: Inspect durable lifecycle history through the browser and API
      Given a cycle has multiple accepted submissions, attempts, results, and transitions
      When its customer or an authorized reviewer opens the cycle history
      Then the browser and API expose the same recorded history
      And the history identifies every submission, attempt, result, and state transition
      And each event records its effective time
      And each result remains associated with its exact submission and attempt
      And later submissions append history rather than overwriting earlier events
      And history retrieval follows the authenticated actor's account permissions

    @IT-64R8S2
    Scenario Outline: Deny another account access to a cycle
      Given a cycle belongs to one customer account
      And a user is authenticated only for another customer account
      When the user requests to <operation> using the protected cycle identifier
      Then the API denies access without disclosing the report, findings, or history
      And the protected cycle and its stored artifacts remain unchanged
      And the denied operation is recorded for security review

      Examples:
        | operation             |
        | retrieve the cycle    |
        | retrieve its history  |
        | retrieve a submission |
        | retrieve its result   |
        | submit a correction   |

  @IT-64R9
  Rule: Lifecycle integration preserves the existing credit policy

    # Integrates IT-25 billable-service facts with IT-45; purchasing is outside scope.
    @IT-64R9S1
    Scenario: Authorize a retail cycle before creating it
      Given a retail customer has no available validation credit
      When the customer requests a new paid validation cycle
      Then the existing credit-authorization capability rejects the request
      And the API creates no pending cycle or paid validation attempt
      And the browser explains the credit requirement

    @IT-64R9S2
    Scenario: Record delivery and credit consumption once for a cycle
      Given a retail cycle has the required credit authorization
      When its first actionable validation result is committed and delivered
      Then one billable-service fact is associated with that cycle and result
      And the existing credit capability consumes one credit exactly once
      And completion retries do not cause an additional debit
      And the lifecycle and credit records remain traceable to the same customer account

    @IT-64R9S3
    Scenario: Revalidate corrections within the same cycle without an additional credit
      Given a retail cycle has already delivered its first actionable result
      When corrected submissions are validated within that open cycle
      Then each correction has its own submission and result history
      And the existing credit capability does not consume another cycle credit

    @IT-64R9S4
    Scenario: Keep cancellations free of delivered-service debits
      Given a retail cycle has been cancelled before an actionable result was delivered
      When the existing credit capability processes the cancellation
      Then no validation credit is consumed for that cycle
      And the cancellation and resulting credit disposition are durably recorded

  @IT-64R10
  Rule: The integrated application preserves the customer and GSE service boundary

    # Integrates IT-25R9 and IT-44R13.
    @IT-64R10S1
    Scenario: Return a passing result without replacing or submitting the customer's report
      Given a customer report has passed and its cycle is closed
      When the customer retrieves the passing result through the browser or API
      Then the response identifies the report, cycle, result, and evaluated coverage
      And the application does not alter the customer's system of record
      And the application does not replace the customer's authoritative report
      And the application does not submit the report to a GSE
      And the displayed result states that the customer remains responsible for GSE submission
