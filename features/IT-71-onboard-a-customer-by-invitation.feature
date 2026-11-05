@IT-71
Feature: Onboard a customer by invitation
  As a prospective UAD customer
  I want to activate an invitation after receiving an invitation
  So that I can establish a customer account with introductory form credits.

  Background:
    Given the introductory form-credit grant is configured as N credits
    And N is a positive whole number

  @IT-71R1
  Rule: An invitation identifies its intended recipient and activation terms

    @IT-71R1S1
    Scenario: Issue an invitation to a prospective customer
      Given an authorized administrator has selected a prospective customer's email address
      When the administrator issues a customer invitation
      Then an invitation is recorded for that email address
      And the invitation has an activation code
      And the invitation has an expiration time
      And the invitation offers N introductory form credits
      And the invitation message explains how to sign in and activate the invitation
      And no customer account or form credits are created by issuing the invitation

    @IT-71R1S2
    Scenario: Prepare invitations from a membership list
      Given an authorized administrator has a membership list approved for invitation use
      When the administrator selects recipients from that list
      Then the selected recipients can be reviewed before invitations are issued
      And selecting recipients does not send invitations
      And selecting recipients does not create customer accounts or form credits

  @IT-71R2
  Rule: A recipient can begin onboarding from a received invitation

    @IT-71R2S1
    Scenario: Receive an actionable customer invitation
      Given a customer invitation has been issued to a prospective customer's email address
      When the prospective customer receives the invitation email
      Then the email identifies UAD as the service being offered
      And the email includes a link to begin invitation onboarding
      And the email includes the invitation activation code
      And the email states when the invitation expires
      And the email describes the offer of N introductory form credits
      And the email explains that the activation code must be entered on first sign-in

    @IT-71R2S2
    Scenario: Open the invitation onboarding link
      Given a prospective customer has received an invitation email
      And the prospective customer is not signed in
      When the prospective customer follows the invitation onboarding link
      Then an invitation onboarding page is displayed
      And the page explains how to establish a sign-in identity or use an existing one
      And the page instructs the customer to use the email address that received the invitation
      And opening the link does not activate the invitation
      And no customer account, membership, or introductory credits are created

    @IT-71R2S3
    Scenario: Establish a sign-in identity for an invited customer
      Given a prospective customer has received a pending invitation
      And the prospective customer does not have a sign-in identity
      When the prospective customer completes identity registration and email verification
      And signs in with the email address that received the invitation
      Then the customer is directed to invitation activation
      And the customer is prompted to enter the invitation activation code
      And identity registration alone does not activate the invitation
      And no customer account, membership, or introductory credits are created yet

    @IT-71R2S4
    Scenario: Use an existing sign-in identity for an invitation
      Given a prospective customer has received a pending invitation
      And the prospective customer already has a sign-in identity for the invited email address
      And the prospective customer has not completed customer onboarding
      When the prospective customer follows the invitation onboarding link
      And signs in with that verified email address
      Then the existing sign-in identity is used
      And no duplicate sign-in identity is created
      And the customer is prompted to enter the invitation activation code

    @IT-71R2S5
    Scenario: Require email verification before invitation activation
      Given a prospective customer has received a pending invitation
      And the prospective customer's sign-in email address has not been verified
      When the prospective customer attempts to proceed to invitation activation
      Then the customer is directed to complete email verification
      And possession of the invitation activation code does not satisfy email verification
      And the invitation remains unactivated
      And no customer account, membership, or introductory credits are created

    @IT-71R2S6
    Scenario: Resume onboarding after leaving before activation
      Given a prospective customer has received a pending invitation
      And the customer has established a verified sign-in identity
      And the customer left onboarding before entering the activation code
      And the invitation has not expired or been revoked
      When the customer returns and signs in with the invited email address
      Then the customer is prompted to enter the invitation activation code
      And the customer does not need to register another sign-in identity
      And no introductory form credits are granted until activation succeeds

  @IT-71R3
  Rule: An invited customer must enter an activation code on first sign-in

    @IT-71R3S1
    Scenario: Request activation after the invited customer first signs in
      Given a pending invitation exists for a prospective customer's email address
      And the prospective customer has not activated that invitation
      When the prospective customer signs in with that verified email address
      Then the customer is prompted to enter the invitation activation code
      And the invitation has not yet created a customer account
      And no introductory form credits have been granted
      And customer-account validation is unavailable until onboarding is completed

    @IT-71R3S2
    Scenario: Activate a valid invitation
      Given a pending invitation exists for a prospective customer's verified email address
      And the invitation has not expired or been revoked
      And the prospective customer is signed in
      And the prospective customer has not previously received an introductory grant
      When the prospective customer enters the matching activation code
      Then a durable UAD user is linked to the authenticated identity
      And a customer account is created
      And the UAD user becomes an active owner of that customer account
      And exactly N introductory form credits are granted to that customer account
      And the invitation is recorded as activated by that UAD user
      And the customer can reach the customer-account landing page

    @IT-71R3S3
    Scenario Outline: Reject an unusable activation code
      Given a prospective customer is signed in
      When the prospective customer enters <code_condition>
      Then invitation activation is refused
      And an actionable explanation is displayed
      And no customer account, membership, or introductory credits are created

      Examples:
        | code_condition                         |
        | an unrecognized activation code        |
        | an expired activation code             |
        | a revoked activation code              |
        | a code already activated by another user |

    @IT-71R3S4
    Scenario: Reject activation by a different email identity
      Given an invitation was issued to one email address
      And a prospective customer is signed in with a different verified email address
      When the prospective customer enters that invitation's activation code
      Then invitation activation is refused
      And the customer is instructed to sign in with the invited email address
      And no customer account, membership, or introductory credits are created

    @IT-71R3S5
    Scenario: Keep email verification separate from invitation activation
      Given a prospective customer has completed email verification
      And the prospective customer has a pending invitation
      When the prospective customer reaches invitation activation
      Then the invitation activation code is still required
      And completing email verification does not activate the invitation

  @IT-71R4
  Rule: Invitation activation and its credit grant happen only once

  @IT-71R4S1
    Scenario: Prevent a second introductory grant through self sign-up
      Given a customer previously received introductory form credits through invitation activation
      When the customer attempts to self sign-up again
      Then the customer is informed that the introductory offer has already been used
      And the existing customer account remains available
      And no additional introductory form credits are granted

    @IT-71R4S2
    Scenario: Prevent a second introductory grant through a different invitation
      Given a customer previously received introductory form credits through invitation activation
      And another valid invitation exists for that customer's email address
      When the customer attempts to activate that other invitation
      Then the customer is informed that the introductory offer has already been used
      And the existing customer account remains available
      And no additional introductory form credits are granted

    @IT-71R4S3
    Scenario: Retry a completed activation
      Given a customer has successfully activated an invitation
      When the same customer submits the same activation code again
      Then the existing customer account is returned
      And no duplicate user, customer account, or membership is created
      And no additional introductory form credits are granted

    @IT-71R4S4
    Scenario: Sign in again after activation
      Given a customer has successfully activated an invitation
      When the customer signs in again
      Then the customer can reach the existing customer-account landing page
      And the invitation activation code is not requested again
      And no additional introductory form credits are granted

    @IT-71R4S5
    Scenario: Prevent a second introductory grant through an invitation
      Given a customer previously received introductory form credits through self sign-up
      When the customer attempts to activate a customer invitation
      Then the customer is informed that the introductory offer has already been used
      And the existing customer account remains available
      And no additional introductory form credits are granted

    @IT-71R4S6
    Scenario: Recover from an interrupted activation
      Given a valid invitation is being activated
      When onboarding fails before completion
      Then no partial account activation or partial credit grant is committed
      And the invitation remains available for a safe retry

    @IT-71R4S7
    Scenario: Preserve activation across a server restart
      Given a customer has successfully activated an invitation
      When the application server restarts
      And the customer signs in again
      Then the user identity link and customer-account membership remain available
      And the invitation remains activated
      And the remaining form-credit balance is preserved

  @IT-71R5
  Rule: Invitation onboarding is traceable

    @IT-71R5S1
    Scenario: Record the origin of an introductory credit grant
      When a customer successfully activates an invitation
      Then the onboarding record identifies the invitation and resulting customer account
      And the credit ledger records N credits with reason "Invitation introductory grant"
      And the ledger entry identifies the invitation
      And the activation code is excluded from ordinary application logs