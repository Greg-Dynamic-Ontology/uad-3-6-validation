@IT-67
Feature: Manage credit refunds, payment disputes, and account financial history
  As an authorized customer-account billing administrator
  I want unused-credit refunds and traceable dispute handling
  So that my account balance reflects payments and delivered services accurately

  # Supplements IT-45R7/R8 and preserves append-only account financial history.
  # Unused-credit refunds and dispute holds are the approved policy.
  # Package values come from IT-65; validation debits and failure reversals from IT-66.

  Background:
    Given financial actions follow IT-44 account billing permissions
    And each purchased credit retains its originating purchase and actual paid value
    And credits are distinguished as available, held, or consumed
    And only available credits can authorize a new paid validation
    And financial entries have stable identities and durable audit history

  @IT-67R1
  Rule: Refund only unused purchased credits at their original paid value

    @IT-67R1S1
    Scenario Outline: Calculate an unused-credit refund from the original package
      Given a confirmed purchase issued <package_credits> credits for <price_cents> United States cents
      And <unused_credits> of those credits remain unused and available
      When an authorized refund for those unused credits is approved
      Then the refund amount is <refund_cents> United States cents
      And the calculation uses the originating package price rather than today's catalog or the base price

      Examples:
        | package_credits | price_cents | unused_credits | refund_cents |
        | 100             | 50000       | 100            | 50000        |
        | 500             | 210000      | 10             | 4200         |
        | 1000            | 400000      | 10             | 4000         |

    @IT-67R1S2
    Scenario: Hold eligible credits while their refund is pending
      Given an authorized refund request identifies unused available credits from one purchase
      When the service accepts the refund request
      Then those credits become unavailable for validation before the provider refund is requested
      And the request records its quantity, amount, original payment, actor, and idempotency key
      And concurrent validation cannot consume credits already held for refund

    @IT-67R1S3
    Scenario: Complete a confirmed refund exactly once
      Given eligible credits are held for a recorded refund request
      When a verified provider outcome confirms the refund was issued
      Then the held credits are removed exactly once
      And the ledger links the refund to its original payment and credit issuance
      And the customer receives refund confirmation
      And the balance remains nonnegative

    @IT-67R1S4
    Scenario: Restore availability after a definitively failed refund
      Given unused credits are held for a refund
      When reconciliation confirms that the provider did not issue the refund and the request definitively failed
      Then the refund hold is released exactly once
      And credits subject to another valid hold remain unavailable
      And an unknown or pending provider outcome does not release credits prematurely

    @IT-67R1S5
    Scenario: Reject a refund request for consumed or unavailable credits
      Given a refund request includes consumed credits, credits already refunded, or credits held for another financial action
      When refund eligibility is evaluated
      Then the ineligible request is rejected with the eligible unused quantity identified
      And consumed validation service is not reclassified as unused credit
      And the service does not create a negative balance or issue an excess refund

    @IT-67R1S6
    Scenario: Preserve package attribution when an account holds several purchases
      Given an account holds unused credits purchased at different package prices
      When the customer requests a refund
      Then the approved refund identifies each originating purchase and its eligible quantity
      And each refunded quantity is valued using its own paid price
      And unrelated purchases and their credits remain unchanged

  @IT-67R2
  Rule: A payment dispute holds the related unused credits while unresolved

    @IT-67R2S1
    Scenario: Hold unused credits from a disputed payment
      Given a verified provider event opens a dispute against a captured credit purchase
      When the service records the dispute
      Then the purchase's affected unused credits are held from validation and refund
      And the hold does not exceed the affected unused quantity
      And credits from unrelated undisputed purchases remain available
      And the account shows the dispute and held quantity

    @IT-67R2S2
    Scenario: Escalate disputed value that has already funded validation
      Given a disputed purchase includes consumed credits
      When the dispute is recorded
      Then the consumed portion is flagged for financial review
      And no negative credit balance is silently created
      And delivered validation results and usage history remain unchanged
      And any further account restriction identifies the applicable account policy

    @IT-67R2S3
    Scenario: Release a dispute hold when the payment is retained
      Given unused credits are held solely because of an unresolved dispute
      When a verified final provider outcome resolves the dispute in the merchant's favor
      Then that dispute hold is released exactly once
      And the credits become available unless another valid hold applies
      And no new purchased credits are issued

    @IT-67R2S4
    Scenario: Remove held credits when the payment is reversed
      Given unused purchased credits are held for a dispute
      When a verified final provider outcome reverses the payment
      Then the affected held credits are removed exactly once
      And previously consumed value remains recorded for financial review
      And the ledger links the reversal to the original payment and dispute

    @IT-67R2S5
    Scenario: Coordinate duplicate and out-of-order financial events
      Given refund and dispute events concern the same purchase
      When notifications are repeated, concurrent, or arrive out of order
      Then their verified current financial outcome is reconciled before credits are released or removed
      And the same credit is not refunded, restored, or removed twice
      And unresolved discrepancies remain visible for review

  @IT-67R3
  Rule: Financial state remains durable and auditable

    @IT-67R3S1
    Scenario: Review account purchases, usage, refunds, and balance
      Given an account has purchases and credit activity
      When an authorized billing administrator opens its financial history in the browser or API
      Then both views show the same available, held, and consumed credit quantities
      And entries identify their effective times, quantities, monetary amounts, and resulting balances
      And purchases identify package prices, catalog versions, payment status, and receipt references
      And debits identify their validation cycles and attempts
      And refunds, reversals, holds, and compensating entries identify their originating events
      And the balance can be reconciled from the ledger

    @IT-67R3S2
    Scenario: Deny another account access to financial records
      Given financial records belong to one account
      When a user without that account's billing permission requests its history, receipt, or refund action
      Then access is denied through both browser and API
      And no financial details are disclosed or changed
      And the denied action is auditable

    @IT-67R3S3
    Scenario: Recover a financial operation across restart
      Given a purchase, debit, refund, dispute, or reversal has a committed identity and recorded state
      When the application restarts and receives a retry or provider reconciliation outcome
      Then it continues from the last committed state
      And it does not duplicate charges, credit issuance, holds, removals, or refunds
      And an interrupted local operation does not expose partially committed balances

    @IT-67R3S4
    Scenario: Preserve original financial records when correcting a mistake
      Given a recorded financial entry requires an authorized correction
      When the correction is committed
      Then a linked adjustment records its reason and actor
      And the original entry remains available
      And all account views show the corrected reconciled balance
