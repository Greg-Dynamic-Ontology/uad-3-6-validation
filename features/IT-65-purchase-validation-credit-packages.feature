@IT-65
Feature: Purchase account-owned UAD validation credit packages
  As an authorized customer-account billing administrator
  I want to purchase a defined package of validation credits
  So that my account can pay for UAD report validation

  # Supersedes the package examples in IT-45R1S1 and the $1,500 balance and
  # daily loaded-value limits in IT-45R5 for the packages specified here.
  # These packages do not require commercial invoicing solely because of value.
  # Other IT-44 account and permission requirements remain in force.
  # Payment-provider selection is deferred; these are provider-independent contracts.

  Background:
    Given customer accounts and billing permissions are governed by IT-44
    And the payment integration uses a configured external payment provider
    And the server maintains a versioned credit-package catalog
    And monetary amounts are recorded in exact United States dollar cents
    And payments and credit-ledger changes are durably recorded

  @IT-65R1
  Rule: The customer buys a package at its recorded catalog price

    @IT-65R1S1
    Scenario Outline: Offer the approved credit packages
      When an authorized billing administrator views available credit packages
      Then the catalog offers <credits> credits for <price_cents> United States cents
      And it identifies the package and catalog version
      And it displays the total price and credit quantity before payment

      Examples:
        | credits | price_cents |
        | 100     | 50000       |
        | 500     | 210000      |
        | 1000    | 400000      |

    @IT-65R1S2
    Scenario: Preserve an accepted purchase quote when catalog prices change
      Given an account has a recorded purchase quote identifying its package, quantity, price, currency, and catalog version
      When a new catalog version changes a package price
      Then the recorded quote retains its original terms for its configured validity period
      And a new purchase uses the currently effective catalog version
      And the customer must accept a new quote if the earlier quote is no longer valid

    @IT-65R1S3
    Scenario: Reject client-supplied price or quantity changes
      Given the customer selects a catalog package
      When a purchase request substitutes a different price, currency, or credit quantity
      Then the server rejects the inconsistent purchase request
      And no payment or credit issuance is initiated for the substituted terms

    @IT-65R1S4
    Scenario Outline: Permit a package that exceeds the former retail limit
      Given an active account is authorized to purchase credits
      When its billing administrator selects the <credits> credit package
      Then the package can proceed to checkout at its catalog price
      And the former $1,500 balance and daily loaded-value limits do not reject the purchase

      Examples:
        | credits |
        | 500     |
        | 1000    |

  @IT-65R2
  Rule: Checkout belongs to the verified customer account

    @IT-65R2S1
    Scenario: Start hosted checkout for the selected account and package
      Given a signed-in user has active credit-purchasing permission in a customer account
      When the user confirms a package purchase
      Then the server records a pending purchase with a stable identity and the accepted quote
      And the server creates a provider-hosted checkout associated with that purchase
      And payment-card entry is handled by the payment provider
      And the purchase records the verified actor and customer account
      And no credits are issued merely because checkout started

    @IT-65R2S2
    Scenario: Deny a purchase without account billing permission
      Given a user lacks active credit-purchasing permission in the requested account
      When the user requests checkout through the browser or API
      Then access is denied
      And no checkout, purchase obligation, or credit issuance is created
      And client-supplied actor identities do not replace verified authorization

    @IT-65R2S3
    Scenario: Reuse checkout when the same purchase request is retried
      Given an account-scoped purchase request has been recorded with an idempotency key
      When the same purchase request is repeated with the same key
      Then the existing purchase and its checkout outcome are returned
      And a second chargeable purchase is not created
      And reuse of that key with different purchase terms is rejected

  @IT-65R3
  Rule: Only a verified captured payment issues purchased credits

    @IT-65R3S1
    Scenario Outline: Credit a confirmed package purchase exactly once
      Given a pending purchase records <credits> credits for <price_cents> United States cents
      When the server verifies that the provider captured that amount in the correct currency for that purchase
      Then exactly <credits> purchased credits are issued to the recorded customer account
      And the ledger links the credits to the purchase, captured payment, and catalog version
      And the customer receives a payment receipt
      And the browser shows the updated available-credit balance

      Examples:
        | credits | price_cents |
        | 100     | 50000       |
        | 500     | 210000      |
        | 1000    | 400000      |

    @IT-65R3S2
    Scenario Outline: Preserve the balance when payment is not captured
      Given an account has a pending package purchase
      When its payment outcome is <outcome>
      Then no purchased credits are issued
      And the browser accurately identifies the purchase state
      And the existing credit balance is unchanged

      Examples:
        | outcome                 |
        | declined                |
        | canceled                |
        | pending                 |
        | authorized but uncaptured |

    @IT-65R3S3
    Scenario: Do not trust a browser success redirect as payment confirmation
      Given the browser returns from checkout claiming success
      And no captured payment has been independently verified
      When the customer views the purchase
      Then the purchase remains unconfirmed
      And no credits are issued from browser-supplied success parameters

    @IT-65R3S4
    Scenario: Reject an unauthenticated provider notification
      Given a payment notification fails provider-origin verification
      When the service receives the notification
      Then no financial or credit state is changed
      And the rejection is recorded for review without exposing payment secrets

    @IT-65R3S5
    Scenario: Hold an inconsistent captured payment for reconciliation
      Given a captured-payment notification has verified provider origin
      But its amount, currency, purchase reference, or merchant environment does not match the recorded purchase
      When the service reconciles the notification
      Then no credits are issued from that inconsistent notification
      And the payment and discrepancy are retained for financial review

    @IT-65R3S6
    Scenario: Apply repeated and concurrent payment notifications once
      Given a captured payment corresponds to one recorded purchase
      When its successful outcome arrives repeatedly or concurrently with different notification identities
      Then that payment issues the purchased credits only once
      And notification identity alone does not permit duplicate issuance
      And an older pending notification does not undo the confirmed capture

  @IT-65R4
  Rule: Payment and credit records survive interruption

    @IT-65R4S1
    Scenario: Recover a captured payment after a lost notification or application restart
      Given the provider captured a recorded purchase
      And local confirmation has not completed
      When reconciliation verifies the provider outcome after the application restarts
      Then the purchase and its credit issuance are completed exactly once
      And the customer can retrieve the durable purchase and updated balance

    @IT-65R4S2
    Scenario: Avoid partial payment-confirmation commits
      Given a verified captured payment is being applied
      When storage fails before the local purchase and credit issuance commit
      Then no partially issued package is exposed as available credits
      And retrying confirmation can complete the purchase without another payment

    @IT-65R4S3
    Scenario: Recover receipt delivery without repeating the financial transaction
      Given a captured purchase and its credit issuance are committed
      When receipt delivery fails
      Then the purchase remains paid and its credits remain issued
      And receipt delivery can be retried without another charge or credit issuance
