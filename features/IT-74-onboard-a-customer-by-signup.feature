@IT-74
Feature: Onboard a customer by signup
  As a prospective UAD customer
  I want to sign up without receiving an invitation
  So that I can establish a customer account with introductory form credits.

  Background:
    Given the introductory form-credit grant is configured as N credits
    And N is a positive whole number

  @IT-74R1
  Rule: A prospective customer can begin signup from the public UAD page

    @IT-74R1S1
    Scenario: Find the signup entry point
      Given a prospective customer is viewing the public UAD landing page
      When the prospective customer chooses to sign up
      Then the signup page is displayed
      And the page describes the offer of N introductory form credits
      And the page explains how to establish a sign-in identity or use an existing one
      And an invitation activation code is not required

    @IT-74R1S2
    Scenario: View signup without creating an account
      Given a prospective customer is viewing the signup page
      When the prospective customer leaves without completing signup
      Then no customer account, membership, or introductory credits are created


  @IT-74R2
  Rule: Signup requires a verified sign-in identity

    @IT-74R2S1
    Scenario: Establish a sign-in identity for a new customer
      Given a prospective customer has begun signup
      And the prospective customer does not have a sign-in identity
      When the prospective customer completes identity registration and email verification
      And signs in with that verified email address
      Then the customer is directed to complete customer-account signup
      And a verified sign-in identity is available for linking to a UAD user
      And identity registration alone does not create a customer account
      And no introductory form credits are granted yet

    @IT-74R2S2
    Scenario: Use an existing sign-in identity
      Given a prospective customer has begun signup
      And the prospective customer already has a verified sign-in identity
      And the prospective customer has not completed customer onboarding
      When the prospective customer signs in
      Then the existing sign-in identity is used
      And no duplicate sign-in identity is created
      And the customer is directed to complete customer-account signup

    @IT-74R2S3
    Scenario: Require email verification before completing signup
      Given a prospective customer has begun signup
      And the customer's sign-in email address has not been verified
      When the prospective customer attempts to complete signup
      Then the customer is directed to complete email verification
      And no customer account, membership, or introductory credits are created

    @IT-74R2S4
    Scenario: Require authentication before completing signup
      Given a prospective customer is not signed in
      When the prospective customer attempts to complete customer-account signup
      Then the customer is directed to sign in
      And no customer account, membership, or introductory credits are created

    @IT-74R2S5
    Scenario: Resume signup after establishing a sign-in identity
      Given a prospective customer has established a verified sign-in identity
      And the customer left before completing customer-account signup
      When the customer returns and signs in
      Then the customer can resume customer-account signup
      And the customer does not need to register another sign-in identity
      And no introductory form credits are granted until signup succeeds


  @IT-74R3
  Rule: Successful signup establishes a customer account

    @IT-74R3S1
    Scenario: Complete signup without an invitation
      Given a prospective customer is signed in with a verified email address
      And the customer has supplied the required customer-account information
      And the customer has no pending invitation for that email address
      And the customer has not previously completed customer onboarding
      And the customer has not previously received an introductory grant
      When the prospective customer completes signup
      Then a durable UAD user is linked to the authenticated identity
      And a customer account is created
      And the UAD user becomes an active owner of that customer account
      And exactly N introductory form credits are granted to that customer account
      And signup is recorded as complete
      And the customer can reach the customer-account landing page
      And no invitation activation code is requested

    @IT-74R3S2
    Scenario: Explain missing customer-account information
      Given a prospective customer is signed in with a verified email address
      And required customer-account information is missing
      When the prospective customer attempts to complete signup
      Then signup is not completed
      And the missing information is identified
      And the customer can correct the information and try again
      And no customer account, membership, or introductory credits are created

    @IT-74R3S3
    Scenario: Direct an invited customer to invitation activation
      Given a prospective customer is signed in with a verified email address
      And a pending invitation exists for that email address
      And the invitation has not expired or been revoked
      When the prospective customer attempts to complete signup
      Then the customer is directed to enter the invitation activation code
      And no separate signup account or introductory grant is created


  @IT-74R4
  Rule: Signup and its introductory credit grant happen only once

  @IT-74R4S1
  Scenario: Retry a completed signup
      Given a customer has successfully completed signup
      When the same customer submits the signup completion request again
      Then the existing customer account is returned
      And no duplicate user, customer account, or membership is created
      And no additional introductory form credits are granted

    @IT-74R4S2
    Scenario: Sign in after completing signup
      Given a customer has successfully completed signup
      When the customer signs in again
      Then the customer can reach the existing customer-account landing page
      And signup is not requested again
      And no invitation activation code is requested
      And no additional introductory form credits are granted

    @IT-74R4S3
    Scenario: Prevent a second introductory grant after invitation activation
      Given a customer previously completed onboarding by invitation
      And the customer received introductory form credits
      When the customer attempts to complete signup
      Then the existing customer account is returned
      And the customer is informed that the introductory offer has already been used
      And no duplicate user, customer account, or membership is created
      And no additional introductory form credits are granted

    @IT-74R4S4
    Scenario: Handle concurrent signup completion requests
      Given a prospective customer is eligible to complete signup
      When multiple signup completion requests for the same authenticated identity arrive concurrently
      Then exactly one customer account is created for that onboarding
      And exactly one owner membership is created
      And exactly one grant of N introductory form credits is recorded
      And the successful responses identify the same customer account

    @IT-74R4S5
    Scenario: Recover from an interrupted signup
      Given an eligible prospective customer is completing signup
      When onboarding fails before completion
      Then no partial account creation or partial credit grant is committed
      And signup is not recorded as complete
      And the customer can safely retry signup

    @IT-74R4S6
    Scenario: Preserve signup across a server restart
      Given a customer has successfully completed signup
      When the application server restarts
      And the customer signs in again
      Then the user identity link and customer-account membership remain available
      And signup remains recorded as complete
      And the remaining form-credit balance is preserved

  @IT-74R5
  Rule: Introductory form credits belong to the customer account

    @IT-74R5S1
    Scenario: Display the introductory credit balance
      Given a customer has just completed signup
      And no form credits have been consumed
      When the customer views the customer-account credit balance
      Then the available balance is N form credits

    @IT-74R5S2
    Scenario: Keep another customer's credits inaccessible
      Given two customers have separate customer accounts
      And neither customer has a membership in the other's account
      And each account has received introductory form credits
      When one customer accesses their account's form credits
      Then only that account's credit balance is available
      And the customer cannot spend the other account's credits

  @IT-74R6
  Rule: Signup onboarding is traceable

  @IT-74R6S1
    Scenario: Trace the customer account to the UAD user
      Given a customer has successfully completed signup
      When the customer account is queried
      Then the linked UAD user is identified

    @IT-74R6S2
    Scenario: Trace the UAD user to the customer account
      Given a customer has successfully completed signup
      When the UAD user is queried
      Then the linked customer account is identified

    @IT-74R6S3
    Scenario: Trace the introductory grant to the customer account
      Given a customer has successfully completed signup
      When the credit ledger is queried for that grant
      Then the resulting customer account is identified

    @IT-74R6S4
    Scenario: Record the origin of an introductory credit grant
      When a customer successfully completes signup
      Then the onboarding record identifies signup as the account's origin
      And the onboarding record identifies the UAD user and customer account
      And the credit ledger records N credits with reason "Signup introductory grant"
      And the ledger entry identifies the resulting customer account
      And the introductory grant can be traced to the completed signup