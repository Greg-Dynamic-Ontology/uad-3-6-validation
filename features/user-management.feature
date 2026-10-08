@IT-2
Feature: Manage single-user and company-user accounts
  WorkOS AuthKit provides hosted registration, sign-in, credential recovery,
  and authentication factors. UAD integrates those services.
  In this feature, a user account is the local UAD application record.
  WorkOS authentication identities and local UAD accounts are separate records.
  UAD manages application user data, company links, and application permissions.
  Company membership alone does not grant every application permission.
  The local company link remains authoritative for UAD account kind.
  WorkOS organization membership does not by itself change that link.
  Each local UAD account is linked to one WorkOS user ID in the configured environment.
  Single-user and company-user accounts share the same user data.
  The shared display_name is required and must contain non-whitespace text.
  A company-user account links to an existing company record.
  A single-user account has no company link.

  # R1-R4 describe local UAD account behavior. They do not implement authentication.
  # Existing R1S1 and R1S2 tests remain local service regression evidence.
  # R5-R6 add WorkOS integration acceptance criteria; they are not yet GREEN.
  # No global authentication Background is added to the existing local scenarios.

  @IT-2R1
  Rule: Both account kinds use the same user data

    @IT-2R1S1 @Create_a_single-user_account
    Scenario: Create a single-user account
      Given valid user account data
      When the account is created without a company link
      Then the user account is saved
      And its company link is null
      And it is a single-user account

    @IT-2R1S2 @Create_a_company-user_account
    Scenario: Create a company-user account
      Given valid user account data
      And an existing company record
      When the account is created with a link to that company record
      Then the user account is saved
      And its company link identifies that company record
      And it is a company-user account

    @IT-2R1S3 @Apply_shared_user_data_requirements
    Scenario: Apply the same user data requirements to both account kinds
      Given user account data whose display_name is missing, empty, or whitespace-only
      When account creation is attempted for either account kind
      Then creation is rejected for the same unmet requirement
      And no user account is saved

  @IT-2R2
  Rule: A company link identifies an existing company record

    @IT-2R2S1 @Reject_a_link_to_a_nonexistent_company
    Scenario: Reject a link to a nonexistent company
      Given valid user account data
      And a company identifier that does not identify an existing company record
      When account creation is attempted with that company identifier
      Then creation is rejected
      And the result explains that the company does not exist
      And no user account is saved

    @IT-2R2S2 @Associate_multiple_users_with_one_company
    Scenario: Associate multiple users with one company
      Given an existing company record
      When two user accounts are created with links to that company
      Then each user account retains its own user data
      And both company links identify the same company record

  @IT-2R3
  Rule: Updating shared user data preserves company membership

    @IT-2R3S1 @Update_a_single-user_account
    Scenario: Update a single-user account
      Given an existing single-user account
      When its shared user data is updated with valid values
      Then the updated user data is saved
      And its company link remains null

    @IT-2R3S2 @Update_a_company-user_account
    Scenario: Update a company-user account
      Given an existing company-user account
      When its shared user data is updated with valid values
      Then the updated user data is saved
      And its company link remains unchanged

  @IT-2R4
  Rule: Account kind follows the company link

    @IT-2R4S1 @Associate_a_single-user_account_with_a_company
    Scenario: Associate a single-user account with a company
      Given an existing single-user account
      And an existing company record
      When the user account is linked to that company
      Then it is a company-user account
      And its shared user data is preserved

    @IT-2R4S2 @Remove-a-users-company-association
    Scenario: Remove a user's company association
      Given an existing company-user account
      When its company link is cleared
      Then its company link is null
      And it is a single-user account
      And its shared user data is preserved


    @IT-2R4S3 @Reject_an_invalid_company_association_change
    Scenario: Reject an invalid company association change
      Given an existing user account
      When its company link is changed to a nonexistent company record
      Then the change is rejected
      And its existing company link and shared user data are preserved

  @IT-2R5
  Rule: WorkOS authentication controls entry to protected UAD functions

    @IT-2R5S1
    Scenario: Sign in through hosted WorkOS AuthKit
      Given a visitor has no authenticated UAD session
      When the visitor chooses to sign in
      Then UAD sends the visitor to hosted WorkOS AuthKit
      When the visitor completes authentication and UAD validates the sign-in result
      Then UAD establishes an authenticated session for the WorkOS user
      And account setup is required before protected appraisal functions are available if no local account is linked

    @IT-2R5S2
    Scenario: Refuse an unsuccessful or invalid authentication result
      Given a visitor begins sign-in through WorkOS AuthKit
      When authentication fails or UAD cannot validate the sign-in result
      Then UAD does not establish an authenticated session
      And no local user account is created or changed by that result
      And protected appraisal functions remain unavailable

    @IT-2R5S3
    Scenario: Require an authenticated session for protected access
      Given a request has no valid authenticated session
      When the request attempts a protected UAD operation
      Then the operation is not performed
      And protected data is not returned
      And authentication is required

    @IT-2R5S4
    Scenario: Sign out of UAD and its WorkOS session
      Given a user has an authenticated UAD session backed by WorkOS
      When the user signs out
      Then UAD ends its local session and the associated WorkOS session
      And the signed-out session cannot authorize a protected UAD operation

  @IT-2R6
  Rule: A verified WorkOS identity resolves to one local UAD user account

    @IT-2R6S1
    Scenario: Link a newly created UAD account to its authenticated identity
      Given UAD has validated a WorkOS session
      And its WorkOS user ID has no linked local account
      And valid shared user account data is supplied
      And the requested company link is absent or identifies an existing company the user is authorized to join
      When the user completes UAD account setup
      Then one local user account is saved with that company link
      And it is linked to the authenticated WorkOS user ID in the configured environment
      And its account kind follows its company link
      And UAD does not create or store a password for that account

    @IT-2R6S2
    Scenario: Reuse the local account on a later WorkOS sign-in
      Given a local user account is linked to a WorkOS user ID
      When UAD validates a later sign-in for that same WorkOS user ID
      Then UAD resolves the existing local user account
      And no duplicate local user account is created
      And its application user data and company link are preserved
      And a changed sign-in email does not create a different local account

    @IT-2R6S3
    Scenario: Refuse an identity link supplied by the client instead of verified authentication
      Given a user is authenticated with one WorkOS user ID
      When a request supplies a different WorkOS user ID to select or link a local account
      Then the request is rejected
      And the existing identity links and local accounts are unchanged
