@IT-66
Feature: Authorize paid UAD validation and property-linked resubmissions
  As an authorized customer-account validator
  I want free schema checks and a bounded paid UAD validation allowance
  So that one credit buys up to ten validations on the same property

  # Supersedes IT-45R3S1 and IT-64R9S2 debit timing: debit at execution start,
  # rather than first actionable result. Service failures are reversed below.
  # Bounds IT-45's formerly unlimited in-cycle corrections to ten total results.
  # Supplements IT-25 cycle identity and submission history; a code is not a cycle ID.
  # A passing result may close its IT-25 cycle but does not end the property's
  # remaining paid allowance. An explicitly linked successor cycle can use it.
  # Supersedes any IT-45/IT-64 requirement to debit another credit solely because
  # the prior cycle passed and closed while this property allowance remains.

  Background:
    Given customer identity and account validation permission are verified
    And account credits are durably recorded under IT-65 and IT-67
    And a paid validation allowance belongs to one account and subject-property address
    And each cycle using that allowance explicitly references the same entitlement
    And one credit covers the initial completed UAD validation and at most nine completed resubmissions
    And submitted XML content and filenames may differ while identifying the same subject property
    And free schema checks do not constitute paid UAD validation
    And the server is authoritative for credit eligibility and remaining allowance

  @IT-66R1
  Rule: Schema validation is free

    @IT-66R1S1
    Scenario Outline: Validate a schema without account credits
      Given a request is permitted by the existing schema-validation access policy
      And the customer has <credits> available credits
      When the customer requests schema validation
      Then the schema-validation result is returned without a credit debit
      And no paid cycle or resubmission code is created by that schema check
      And no paid validation allowance is consumed

      Examples:
        | credits |
        | 0       |
        | 1       |

  @IT-66R2
  Rule: Available credits control starting a new paid validation

    @IT-66R2S1
    Scenario Outline: Reflect account credit eligibility in the browser
      Given an authorized validator has selected an account with <credits> available credits
      When the report-validation page is displayed
      Then the new paid UAD validation button is <button_state>
      And the page displays the available-credit balance
      And an unavailable paid action explains how to purchase credits
      And the free schema-validation action remains governed by its independent access policy

      Examples:
        | credits | button_state |
        | 0       | disabled     |
        | 1       | enabled      |

    @IT-66R2S2
    Scenario: Enforce the credit requirement on the server
      Given an account has no available credit for a new paid cycle
      When a client submits a paid-validation request directly to the API
      Then the server rejects the new paid execution
      And no validation worker starts and no negative balance is created
      And a stale or modified browser button cannot bypass that decision

    @IT-66R2S3
    Scenario: Consume one credit when the first paid execution starts
      Given an eligible new cycle has an accepted ingestible submission
      And the account has one available credit
      When the server commits the transition that authorizes its first UAD validation execution to start
      Then exactly one credit is debited before validation execution proceeds
      And the debit is linked to the account, cycle, and initial attempt
      And an allowance of ten total completed UAD validations is established
      And starting checkout, uploading a file, or performing a free schema check is not this debit boundary

    @IT-66R2S4
    Scenario: Prevent concurrent cycles from spending the same last credit
      Given an account has one available credit
      When two new paid cycles concurrently request execution start
      Then at most one execution obtains the credit and starts
      And the other request receives an insufficient-credit outcome
      And the credit decision and execution authorization are durably coordinated

    @IT-66R2S5
    Scenario: Recover an authorized execution without debiting twice
      Given a cycle's start authorization and credit debit were committed
      When its request is retried or the application restarts before execution completes
      Then the recorded attempt is recovered according to its execution state
      And the same start authorization does not consume another credit
      And concurrent duplicate execution is prevented

  @IT-66R3
  Rule: An emailed code identifies a property-linked resubmission entitlement

    @IT-66R3S1
    Scenario: Issue a code for a paid cycle
      Given a new paid cycle has its credit debit and execution authorization committed
      And the subject-property address can be recorded unambiguously
      When the resubmission entitlement is recorded
      Then it has a code that is impractical to guess
      And the code is linked to the account, cycle, recorded subject-property address, and ten-validation allowance
      And the code is emailed to the verified requesting user's email address
      And delivery is recorded without placing the usable code in general application logs

    @IT-66R3S2
    Scenario: Retry code email delivery without recreating the entitlement
      Given a cycle's resubmission entitlement is durably recorded
      When sending its email fails
      Then the delivery failure is visible and retryable
      And retrying delivery does not debit a credit or reset the allowance
      And resending follows the same account authorization checks

    @IT-66R3S3
    Scenario: Require account authorization as well as the code
      Given a resubmission code belongs to one customer account
      When an unauthenticated user or a user without that account's validation permission presents the code
      Then the request is denied
      And the code alone does not disclose a report, address, result, or account history
      And no allowance or credit is consumed

    @IT-66R3S4
    Scenario: Reject an unknown or revoked code
      Given an otherwise authorized customer submits an unknown or revoked resubmission code
      When resubmission eligibility is evaluated
      Then no resubmission is started
      And no cycle is inferred from filenames or property addresses alone
      And no credit or allowance is consumed

  @IT-66R4
  Rule: An included validation must belong to the paid entitlement's property

    @IT-66R4S1
    Scenario: Accept corrected XML under the existing entitlement
      Given an account has a paid entitlement with remaining allowance and a valid code
      And a corrected submission identifies the same subject-property address
      When an authorized validator submits the correction with that code
      Then the server resolves the account-owned property entitlement
      And the submission uses its explicitly identified open cycle or an authorized linked successor cycle
      And a new submission and attempt preserve their own identities and content digests
      And the corrected file need not have the same byte content or filename as the initial file
      And no additional credit is debited

    @IT-66R4S2
    Scenario: Reject a different property's report under an existing code
      Given a valid code is linked to one subject-property address
      When a resubmitted report identifies a different subject property
      Then the report is not executed under that entitlement
      And the customer is told that a new paid cycle is required for a different property
      And the existing cycle, debit, and allowance remain unchanged

    @IT-66R4S3
    Scenario: Require explicit entitlement linkage even when property addresses match
      Given two appraisals concern the same property address
      When a customer requests validation without identifying the existing paid entitlement through its valid code
      Then the address alone does not select or grant a paid entitlement
      And the customer can supply the code to use its remaining property allowance
      And no new credit is charged without explicit authorization for a new purchase-funded allowance

    @IT-66R4S4
    Scenario: Resolve address ambiguity before reusing an entitlement
      Given a proposed resubmission has a missing, changed, or ambiguous subject-property address
      When the service cannot verify that it belongs to the recorded property
      Then the service does not silently reuse the paid entitlement
      And it requests correction or authorized review before execution
      And approved address clarification is audited without resetting usage or transferring the entitlement to another property

  @IT-66R5
  Rule: One credit covers at most ten completed UAD validations on the same property

    @IT-66R5S1
    Scenario Outline: Count completed validations against the allowance
      Given a paid property entitlement has <completed_before> completed UAD validations across its linked cycles
      And its code and property linkage are valid
      When its next authorized resubmission returns an actionable UAD result
      Then the completed count becomes <completed_after>
      And the remaining allowance becomes <remaining>
      And no additional credit is debited
      And the count includes passing results and results containing governed findings

      Examples:
        | completed_before | completed_after | remaining |
        | 1                | 2               | 8         |
        | 9                | 10              | 0         |

    @IT-66R5S2
    Scenario: Permit an included correction when the account balance is zero
      Given an authorized account has zero available credits
      And it has a paid property entitlement with valid code, matching property, and remaining allowance
      When the customer opens that cycle's correction workflow
      Then the included resubmission action is available
      And the new paid-cycle action remains disabled
      And executing the included correction does not require another credit

    @IT-66R5S3
    Scenario: Require an explicit new paid cycle after the tenth validation
      Given a property entitlement has completed ten UAD validations under one credit across its linked cycles
      When the customer requests another validation under its code
      Then the included request is rejected without execution
      And the UI explains that the allowance is exhausted
      And no extra credit is silently charged
      And an explicitly authorized new cycle requires another available credit

    @IT-66R5S4
    Scenario: Prevent retries and concurrency from corrupting allowance usage
      Given a property entitlement has one remaining included validation across its linked cycles
      When concurrent resubmissions or repeated completion events arrive
      Then at most one new distinct attempt uses that remaining place
      And an account-scoped retry returns the existing request outcome
      And each distinct completed attempt increments usage exactly once

    @IT-66R5S5
    Scenario: Preserve the property's remaining allowance after a passing result
      Given a paid property entitlement has completed fewer than ten UAD validations
      And its latest report passed and its cycle closed according to IT-25
      When an authorized customer supplies the valid code for another validation on the same property
      Then an explicitly linked successor cycle can use the remaining entitlement
      And no additional credit is required or debited
      And the earlier passing cycle and its results remain unchanged
      And the total completed count is maintained across all cycles using that entitlement
      And a passing result does not reset the count or terminate the remaining allowance

  @IT-66R6
  Rule: Processing failures do not leave a customer charged for undelivered validation

    @IT-66R6S1
    Scenario: Reject an unprocessable upload before starting paid execution
      Given an uploaded artifact cannot be ingested as a UAD appraisal report
      When the service evaluates it before execution start
      Then no credit is debited and no allowance is consumed
      And the customer receives the processing diagnostic

    @IT-66R6S2
    Scenario: Reverse the initial debit when service failure prevents an actionable result
      Given a cycle's initial execution consumed one credit at start
      When a service failure prevents delivery of an actionable UAD result
      Then a linked compensating entry restores that credit exactly once
      And the failed attempt is retained without a completed-validation count
      And the cancelled cycle's code cannot authorize further execution
      And a new attempt follows the existing cancellation and new-cycle rules

    @IT-66R6S3
    Scenario: Preserve remaining allowance when an included execution fails
      Given an open paid cycle has already delivered its initial actionable result
      When an included resubmission fails operationally before producing an actionable result
      Then its failed attempt and reason are recorded
      And its allowance place is released exactly once
      And the original paid credit is not refunded merely because this correction failed
      And the previous authoritative result remains available

    @IT-66R6S4
    Scenario: Preserve billing and allowance knowledge across restart
      Given a debit, reversal, entitlement, completed count, or code-delivery event has committed
      When the application restarts and an authorized user retrieves the cycle
      Then its recorded payment linkage, usage, remaining allowance, and property association remain consistent
      And retrieval does not debit credits, consume allowance, or send another email
