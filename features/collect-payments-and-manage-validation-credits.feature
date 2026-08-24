@otdd @billing @validation-credits
Feature: Collect payments and manage UAD validation credits

As a retail customer
I want to prepay for UAD report validation credits
So that I can open validation cycles without paying separately for each submission

Background:
Given one UAD Validation Credit pays for billable validation service delivered within one report-validation cycle
And corrected versions of the report can be revalidated within that cycle until the report passes
And retail credits are closed-loop and usable only for UAD validation services
And the retail credit-value limit is $1,500
And all monetary amounts are denominated in United States dollars

Rule: Issue purchased credits only for verified successful payments

@otdd-credit-s-01
Scenario Outline: Purchase a validation-credit package
Given the customer has an active retail account
And the customer's balance can accept the purchased credit value without exceeding the retail limits
When the customer purchases <credits> validation credits for <price>
And the payment provider authorizes and captures the payment
Then <credits> purchased credits are added to the customer's account exactly once
And the customer receives a payment receipt
And the credit ledger records the payment identifier
And the credit ledger records the purchased quantity and value
And the account displays the updated available-credit balance

Examples:
| credits | price |
| 10      | $25   |
| 50      | $99   |
| 250     | $375  |

@otdd-credit-s-02
Scenario: Do not issue credits for a failed payment
Given the customer attempts to purchase validation credits
When the payment is declined or cannot be completed
Then no validation credits are added to the account
And no successful purchase is recorded
And the customer is told that the payment did not complete
And the customer's existing credit balance is unchanged

@otdd-credit-s-03
Scenario: Process a payment notification exactly once
Given a captured payment has already added its validation credits
When the payment provider sends the same successful-payment notification again
Then no additional validation credits are added
And the duplicate notification is recorded for audit
And the payment remains associated with one credit-ledger entry

@otdd-credit-s-04
Scenario: Reject an unverified payment notification
Given a payment notification cannot be authenticated as originating from the payment provider
When the service receives the notification
Then no validation credits are added or removed
And the notification is recorded as rejected
And the event is available for security review

Rule: Treat unused purchased credits as unfulfilled customer obligations

@otdd-credit-s-05
Scenario: Record purchased credits as an unfulfilled customer obligation
Given the customer has purchased unused validation credits
When the payment and credits are recorded
Then the unused purchased value is recorded as an unfulfilled customer obligation
And no validation-service revenue is attributed to an unused credit

Rule: Consume one credit only when billable validation service is delivered for a cycle

@otdd-credit-s-06
Scenario: Consume one credit when the first actionable result delivers billable validation service
Given the customer has at least one available validation credit
And the customer has a pending report-validation cycle for a newly submitted report
When the service returns the cycle's first actionable validation result
And the lifecycle records that billable validation service was delivered
Then one validation credit is consumed exactly once
And the debit is associated with the pending cycle and its actionable result
And the credit ledger records the debit and resulting balance
And the consumed credit is associated with delivered validation service

@otdd-credit-s-07
Scenario: Do not consume a credit for an unprocessable upload
Given a pending report-validation cycle has an accepted upload
When the upload cannot be ingested as a UAD appraisal report
Then no validation credit is consumed
And the pending cycle is cancelled
And the lifecycle records that no billable validation service was delivered
And the customer is told why the upload could not be processed

@otdd-credit-s-08
Scenario: Do not consume a credit when the validation service fails
Given a pending report-validation cycle has an accepted submission
When a service failure prevents the service from returning an actionable validation result
Then no validation credit is consumed
And the pending cycle is cancelled
And the lifecycle records that no billable validation service was delivered
And the failed attempt is recorded for operational review

@otdd-credit-s-09
Scenario: Require credit authorization before creating a pending retail validation cycle
Given the customer has no available validation credits
When the customer submits a new UAD appraisal report
Then no pending report-validation cycle is created
And the report is not validated as a paid retail report
And the customer is invited to purchase validation credits

@otdd-credit-s-10
Scenario: Revalidate a corrected report without consuming another credit
Given a report-validation cycle is open
And one validation credit has already been consumed for the cycle
And the customer corrected the report in the customer's system of record
When the customer submits a corrected version of the same report
Then the corrected report is validated within the existing cycle
And no additional validation credit is consumed
And the new validation result is added to the cycle history

@otdd-credit-s-11
Scenario: Close a validation cycle when the report passes
Given a report-validation cycle is open
When a submitted version of the report passes validation
Then the validation cycle is marked as passed and closed
And the passing validation result is retained in the cycle history
And the customer is told that the report can be submitted to the GSE
And the validation service does not submit the report to the GSE

@otdd-credit-s-12
Scenario: Open a new cycle for a report submitted after its prior cycle closed
Given a report's prior validation cycle is closed
And the customer has at least one available validation credit
When the customer requests validation of a subsequently submitted version as a new cycle
Then a new pending report-validation cycle is created
And the new cycle retains a reference to the prior cycle
And no validation credit is consumed before the new cycle delivers its first actionable validation result

Rule: Replenish credits only through an authorized successful payment

@otdd-credit-s-13
Scenario: Automatically replenish a retail credit balance
Given the customer enabled automatic replenishment
And the customer selected a balance threshold and an approved credit package
And purchasing the package would remain within the retail balance and daily-value limits
When the available-credit balance falls below the selected threshold
And the payment provider captures the replenishment payment
Then the package credits are added exactly once
And the customer receives a replenishment receipt
And the account displays the updated balance

@otdd-credit-s-14
Scenario: Preserve the balance when automatic replenishment fails
Given the customer enabled automatic replenishment
And the available-credit balance falls below the selected threshold
When the replenishment payment fails
Then no validation credits are added
And the existing credit balance is unchanged
And the customer is notified that automatic replenishment failed

Rule: Enforce retail stored-value limits across all loaded value

@otdd-credit-s-15
Scenario: Enforce the $1,500 maximum retail credit-value balance
Given the customer's current retail credit value is less than or equal to $1,500
When a proposed purchase or credit adjustment would increase the balance above $1,500
Then the proposed value is not added
And the customer's balance does not exceed $1,500
And the customer is offered a purchase amount that fits within the limit or commercial invoicing

@otdd-credit-s-16
Scenario: Enforce the $1,500 daily loaded-value limit
Given the customer's beginning-of-day credit value is known
And all purchased, promotional, and adjusted value added today is known
When proposed additional value would cause the beginning-of-day value plus today's loaded value to exceed $1,500
Then the proposed value is not added
And spending credits during the day does not increase today's permitted loaded value
And the customer is told when additional value may be loaded

@otdd-credit-s-17
Scenario: Count promotional credits toward retail limits
Given the customer is eligible to receive promotional validation credits
When the promotional value is evaluated for issuance
Then the promotional value is included in the balance-limit calculation
And the promotional value is included in the daily loaded-value calculation
And purchased and promotional credits remain distinguishable in the ledger

Rule: Keep retail credits closed-loop and nontransferable

@otdd-credit-s-18
Scenario: Prevent transfer or cash withdrawal of retail credits
Given the customer has available retail validation credits
When the customer attempts to transfer credits to an unrelated customer or withdraw them as cash
Then the request is rejected except where cash redemption is required by law
And the available-credit balance remains unchanged
And the rejected request is recorded for audit

Rule: Reverse unused purchased value without corrupting the account balance

@otdd-credit-s-19
Scenario: Refund an unused credit purchase
Given a captured credit purchase is eligible for a refund
And the credits associated with the refund have not been consumed
When the refund is approved and issued
Then the corresponding unused credits are removed exactly once
And the refund is linked to the original payment and credit-ledger entries
And the customer receives a refund confirmation
And the account balance remains nonnegative

@otdd-credit-s-20
Scenario: Escalate a refund or chargeback that exceeds unused purchased value
Given a refund, reversal, or chargeback exceeds the unused purchased value associated with the payment
When the financial event is received
Then the service does not silently create a negative credit balance
And the account is flagged for financial review
And new paid validation cycles may be restricted according to account policy
And the ledger preserves the original event and the resulting adjustment

Rule: Preserve an auditable payment and credit ledger

@otdd-credit-s-21
Scenario: Display an auditable credit history
Given the customer has payment and credit activity
When the customer reviews the account history
Then each entry shows its effective date and type
And each entry shows the credit quantity and monetary value when applicable
And each entry shows the resulting balance
And each entry identifies the related payment, refund, adjustment, or validation cycle
And purchased and promotional credits are distinguishable

Rule: Move qualifying high-volume customers to commercial invoicing

@otdd-credit-s-22
Scenario: Move a high-volume customer to commercial invoicing
Given a customer requires capacity beyond the retail prepaid limits
When the customer is approved for commercial invoicing
Then the customer can be billed periodically for report-validation cycles
And the commercial account does not require a retail prepaid balance
And retail credit limits are not bypassed by placing excess prepaid value in the retail account
And invoiced usage remains auditable by report-validation cycle