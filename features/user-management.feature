@IT-3
Feature: Manage single-user and company-user accounts
  Single-user and company-user accounts share the same user data.
  A company-user account links to an existing company record.
  A single-user account has no company link.

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
      Given user account data that fails a shared user data requirement
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