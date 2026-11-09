@IT-IT-65
Feature: Manage customer accounts
  As a prospective customer or authorized customer-account administrator
  I want to create, view, update, and close a customer account
  So that the account can own validation credits and UAD validation work

  # Establishes the customer-account lifecycle required by IT-64 and IT-65.
  # Existing IT-44 account and permission requirements remain in force.
  # WorkOS manages authentication; UAD manages customer accounts and memberships.
  # Invitation and signup features govern admission and introductory credits.
  # Closing an account is the customer-facing delete operation.
  # Permanent erasure and record-retention policies are outside this feature.

  Background:
    Given customer accounts and permissions are governed by IT-44
    And the user has authenticated through WorkOS
    And UAD identifies the user by a stable UAD user ID
    And the authenticated identity is linked to that UAD user ID
    And customer accounts and memberships are durably stored
    And account changes are attributable to the acting user

    @IT-IT-65R1
  Rule: A customer account has an identity separate from its users

    @IT-IT-65R1S1
    Scenario: Assign a stable identity to a new customer account
      When UAD creates a customer account
      Then it assigns a unique customer-account ID
      And that ID is distinct from the owner's UAD user ID
      And that ID is distinct from the owner's WorkOS user ID
      And subsequent changes to account information preserve that ID

    @IT-IT-65R1S2
    Scenario: Associate account-owned resources with the customer account
      Given an active customer account
      When the account acquires validation credits or creates validation work
      Then those resources belong to the customer-account ID
      And they do not belong personally to the user performing the action

  
  @IT-IT-65R2
  Rule: An eligible user can create a solo or company customer account

    @IT-IT-65R2S1
    Scenario Outline: Create a customer account
      Given the user is eligible to establish a customer account
      When the user submits the required information for a "<account_type>" account
      Then UAD creates one active customer account of that type
      And UAD creates an active owner membership for the user
      And the owner receives the account permissions prescribed by IT-44
      And UAD displays the customer-account ID and account information
      And the account and membership remain available in a later session

      Examples:
        | account_type |
        | solo         |
        | company      |


    @IT-IT-65R2S2
    Scenario: Record required information for a solo customer account
      When the user creates a solo customer account
      Then the required account information is:
        | field                 |
        | account display name  |
        | primary contact name  |
        | primary contact email |
      And optional information is:
        | field                  |
        | contact telephone      |
        | postal address         |
      And omitted optional information does not prevent creation

    @IT-IT-65R2S3
    Scenario: Record required information for a company customer account
      When the user creates a company customer account
      Then the required account information is:
        | field                 |
        | company name          |
        | account display name  |
        | primary contact name  |
        | primary contact email |
      And optional information is:
        | field                  |
        | contact telephone      |
        | postal address         |
        | company website        |
      And omitted optional information does not prevent creation

    @IT-IT-65R2S4
    Scenario: Reject incomplete or invalid account information
      When the user submits account information with a missing or invalid required field
      Then UAD identifies each field requiring correction
      And UAD preserves the submitted information for correction
      And UAD creates neither a customer account nor an owner membership

    @IT-IT-65R2S5
    Scenario: Avoid duplicate accounts when creation is retried
      Given an account-creation request has succeeded
      When the same request is retried
      Then UAD returns the previously created customer account
      And it creates no additional customer account or membership

    @IT-IT-65R2S6
    Scenario: Roll back incomplete account creation
      When UAD cannot durably save both the account and its owner membership
      Then neither change is committed
      And UAD reports that account creation did not complete

  @IT-IT-65R3
  Rule: Authorized users can view their customer accounts


    @IT-IT-65R3S1
    Scenario: List accounts available to the signed-in user
      Given the user has active memberships in customer accounts
      When the user views their customer accounts
      Then UAD lists only accounts the user is authorized to view
      And each entry identifies the account ID, display name, type, and status
      And each entry identifies the user's role in that account

    @IT-IT-65R3S2
    Scenario: View a selected customer account
      Given the user is authorized to view a customer account
      When the user selects that account
      Then UAD displays its stored account information
      And UAD identifies the selected account throughout account-specific work

    @IT-IT-65R3S3
    Scenario: Reject access to an unrelated customer account
      Given the user has no permission to view a customer account
      When the user requests that account using its customer-account ID
      Then UAD denies access
      And it discloses no account details

  @IT-IT-65R4
  Rule: Authorized administrators can update customer-account information

    @IT-IT-65R4S1
    Scenario: Update account information
      Given the user is authorized to administer an active customer account
      When the user submits valid changes to its editable account information
      Then UAD durably stores the changes
      And a subsequent read returns the updated information
      And the customer-account ID remains unchanged
      And account memberships, credits, and validation work remain associated with it
      And UAD records who made the change and when

    Scenario: Reject an invalid update
      Given the user is authorized to administer an active customer account
      When the user submits invalid account information
      Then UAD identifies the information requiring correction
      And the previously stored account information remains unchanged

    Scenario: Reject an unauthorized update
      Given the user is not authorized to administer a customer account
      When the user attempts to change its information
      Then UAD denies the change
      And the stored account information remains unchanged

    Scenario: Detect conflicting updates
      Given two administrators have read the same version of an account
      And one administrator has saved a change
      When the other administrator submits an update based on the earlier version
      Then UAD reports that the account has changed
      And it does not silently overwrite the first administrator's change

  @IT-IT-65R5
  Rule: Company users act through explicit account memberships

    @IT-IT-65R5S1
    Scenario: Associate a user with an existing company account
      Given an active company customer account
      And an authenticated UAD user
      And an account administrator authorized to manage memberships
      When the administrator grants that user a permitted account role
      Then UAD creates an active membership linking the user ID to the customer-account ID
      And it creates no additional customer account
      And the user receives only the permissions granted by that membership

    @IT-IT-65R5S2
    Scenario: Do not infer company membership from an email domain
      Given a user has an email address matching a company's email domain
      But the user has no active membership in that company's customer account
      When the user requests access to that account
      Then UAD denies access

    @IT-IT-65R5S3
    Scenario: Remove a user's company membership
      Given the administrator is authorized to manage account memberships
      And removing the membership will leave an active account owner
      When the administrator removes a user's membership
      Then UAD durably deactivates that membership
      And subsequent account requests from that user are denied unless another active membership permits them
      And the user's identity remains available
      And the account's credits and validation work remain unchanged

    @IT-IT-65R5S4
    Scenario: Prevent removal of the last active owner
      Given a customer account has only one active owner
      When an administrator attempts to remove or demote that owner
      Then UAD rejects the change
      And explains that another active owner must first be designated

  @IT-IT-65R6
  Rule: An authorized owner can close a customer account

    @IT-IT-65R6S1
    Scenario: Close an account with no outstanding obligations
      Given the user is an active owner of a customer account
      And the account has no remaining validation credits
      And the account has no validation work in progress
      And the account has no pending purchases or unresolved payment obligations
      When the owner explicitly confirms account closure
      Then UAD durably marks the account as closed
      And UAD records who closed it and when
      And subsequent attempts to purchase credits or start validation work are rejected
      And existing account history remains associated with the customer-account ID
      And the users' identities and memberships in other accounts remain unchanged

    @IT-IT-65R6S2
    Scenario: Explain why an account cannot yet be closed
      Given the user is an active owner of a customer account
      And the account has remaining credits, work in progress, or unresolved payment obligations
      When the owner requests account closure
      Then UAD identifies the outstanding conditions
      And the account remains active

    @IT-IT-65R6S3
    Scenario: Reject closure by a user without owner permission
      Given the user is not an active owner of a customer account
      When the user attempts to close that account
      Then UAD denies closure
      And the account remains unchanged

    @IT-IT-65R6S4
    Scenario: Repeat an account-closure request
      Given a customer account has already been closed
      When its authorized owner repeats the closure request
      Then UAD reports that the account is already closed
      And it creates no additional closure change