@IT-68
Feature: Capture customer onboarding information
  As a prospective UAD customer
  I want to provide information appropriate to my relationship with a customer account
  So that I can establish a solo account, establish a company account, or join an existing company account.

  @IT-68R1
  Rule: The onboarding path determines which information is required

  @IT-68R1S1
  Scenario: Choose the relationship to a customer account
      Given a prospective customer has begun onboarding
      When the customer is asked how they will use UAD
      Then the available choices are:
        | relationship                       |
        | Establish a solo customer account  |
        | Establish a company customer account |
        | Join an existing company customer account |
      And the information requested reflects the selected relationship
      And choosing a relationship does not itself create an account or membership


  @IT-68R1S2
  Scenario: Distinguish required information from optional information
      Given a prospective customer has selected an onboarding relationship
      When the customer views the information form
      Then every required field is identified as required
      And every optional field is identified as optional
      And the purpose of each requested field is explained
      And optional fields may be left blank

  @IT-68R2
  Rule: Every human user has a verified identity and contact information

    @IT-68R2S1
    Scenario: Require common human-user information
      Given a prospective customer is completing any onboarding relationship
      When the customer provides human-user information
      Then the following information is required:
        | information           | requirement                                      |
        | Sign-in identity      | An authenticated identity with a stable identifier |
        | Email address         | Verified through the sign-in service             |
        | Display name          | A nonblank name used to identify the person in UAD |
        | Phone number          | A valid phone number including its country calling code |
        | Phone verification    | Successful verification of the supplied phone number |
      And a UAD user identifier is assigned by the system
      And the customer is not asked to choose an internal user identifier
      And the customer is not asked to provide a sign-in password to the customer-information form

    @IT-68R2S2
    Scenario: Use verified email information from the sign-in identity
      Given a prospective customer is signed in with a verified email address
      When the customer views their onboarding information
      Then the verified email address is displayed
      And entering another address in an ordinary form does not make it verified
      And another verified identity cannot be selected by editing form fields

    @IT-68R2S3
    Scenario: Reject incomplete required human-user information
      Given a prospective customer has omitted required human-user information
      When the customer attempts to complete onboarding
      Then onboarding is not completed
      And each missing item is identified
      And the customer can supply the missing information and try again
      And no customer account or membership is partially created

    @IT-68R2S4
    Scenario: Require verification of the supplied phone number
      Given a prospective customer has supplied a valid phone number
      And ownership of that phone number has not been verified
      When the customer attempts to complete onboarding
      Then the customer is directed to complete phone verification
      And onboarding is not completed

  @IT-68R3
  Rule: A solo customer supplies information for an individually owned account

    @IT-68R3S1
    Scenario: Require information for a solo customer account
      Given a prospective customer has selected "Establish a solo customer account"
      When the customer views the required account information
      Then the following information is required:
        | information            | requirement                         |
        | Human-user information | The common verified user information |
        | Customer account label | A nonblank name for the solo account |
      And the customer's display name is offered as the initial account label
      And a company name is not required
      And a company membership invitation is not required

    @IT-68R3S2
    Scenario: Accept optional information for a solo customer
      Given a prospective customer has selected "Establish a solo customer account"
      When the customer provides optional information
      Then the following information may be supplied:
        | information                         |
        | Business or trading name            |
        | Business mailing address            |
        | Professional designation            |
        | Appraiser license or credential number |
        | License or credential issuing jurisdiction |
      And supplied optional information is validated for its stated format
      And self-reported credentials are not represented as independently verified

    @IT-68R3S3
    Scenario: Create a solo account without optional information
      Given a prospective customer has supplied all required solo-account information
      And the customer has left all optional fields blank
      And the customer has satisfied the applicable signup or invitation requirements
      When the customer completes onboarding
      Then a solo customer account is created
      And the customer becomes its active owner
      And the account is assigned a system-generated customer account identifier

  @IT-68R4
  Rule: A company customer supplies information about the company and its initial owner


    @IT-68R4S1
    Scenario: Require information for a company customer account
      Given a prospective customer has selected "Establish a company customer account"
      When the customer views the required account information
      Then the following information is required:
        | information               | requirement                                      |
        | Initial owner information | The common verified human-user information       |
        | Company name              | A nonblank company name                          |
        | Customer account label    | A nonblank name used to identify the account in UAD |
        | Authority declaration     | Confirmation that the person is authorized to establish the account for the company |
      And the company name is offered as the initial customer account label
      And the person is informed that they will become the initial account owner


    @IT-68R4S2
    Scenario: Accept optional information for a company customer
      Given a prospective customer has selected "Establish a company customer account"
      When the customer provides optional company information
      Then the following information may be supplied:
        | information                         |
        | Business or trading name            |
        | Business mailing address            |
        | Company website                     |
        | General business phone number       |
        | Initial owner's job title           |
        | Company registration identifier     |
        | Company registration jurisdiction   |
      And supplied optional information is validated for its stated format
      And self-reported company information is not represented as independently verified

    @IT-68R4S3
    Scenario: Create a company account without optional information
      Given a prospective customer has supplied all required company-account information
      And the customer has left all optional fields blank
      And the customer has satisfied the applicable signup or invitation requirements
      When the customer completes onboarding
      Then a company customer account is created
      And the authenticated person becomes its active owner
      And the account is assigned a system-generated customer account identifier
      And the company account is distinct from the owner's human-user identity

    @IT-68R4S4
    Scenario: Require an authority declaration
      Given a prospective customer has supplied the required company and owner information
      And the customer has not confirmed authority to establish the account
      When the customer attempts to complete company-account onboarding
      Then onboarding is not completed
      And the customer is asked to confirm their authority
      And no company customer account is created

    @IT-68R4S5
    Scenario: Keep company names separate from account identity
      Given a company customer account already uses a particular company name
      When another prospective customer supplies the same company name
      Then the name alone does not identify the existing customer account
      And the prospective customer is not granted access to that account
      And account access requires an authorized membership

  @IT-68R5
  Rule: A person joining a company supplies personal information and membership authorization


    @IT-68R5S1
    Scenario: Require information for joining an existing company customer
      Given a prospective member has selected "Join an existing company customer account"
      When the person views the required information
      Then the following information is required:
        | information              | requirement                                      |
        | Human-user information   | The common verified user information             |
        | Company membership invitation | A valid invitation identifying the existing account and intended recipient |
      And the company account is identified from the membership invitation
      And the offered membership roles are identified from the membership invitation
      And the person is not required to re-enter company profile information
      And the person cannot select additional roles by editing onboarding information

    @IT-68R5S2
    Scenario: Accept optional information for a company member
      Given a prospective member is joining an existing company customer account
      When the person provides optional membership information
      Then the following information may be supplied:
        | information                         |
        | Job title                           |
        | Department or team                  |
        | Professional designation            |
        | Appraiser license or credential number |
        | License or credential issuing jurisdiction |
      And omission of optional information does not prevent membership acceptance
      And optional information does not grant additional permissions

    @IT-68R5S3
    Scenario: Join an existing company account
      Given a person has supplied all required human-user information
      And a valid company membership invitation matches the person's verified email address
      And the company customer account is active
      When the person accepts the membership invitation
      Then the person's UAD user is linked to the existing company account
      And the membership has only the roles authorized by the invitation
      And no new company customer account is created
      And the existing company profile is unchanged
      And joining the company does not create a new-customer introductory credit grant


    @IT-68R5S4
    Scenario: Reuse an existing UAD user when joining a company
      Given a person already has a UAD user linked to their authenticated identity
      And the person has received a valid company membership invitation
      When the person accepts the invitation
      Then the existing UAD user is used for the company membership
      And no duplicate UAD user is created
      And memberships in other customer accounts remain unchanged


    @IT-68R5S5
    Scenario: Refuse membership without company authorization
      Given a person has supplied a company name or company account identifier
      And the person does not have a valid company membership invitation
      When the person attempts to join that company customer account
      Then no membership is created
      And the person is instructed to request an invitation from an account owner
      And knowledge of the company name or account identifier does not grant access

    @IT-68R5S6
    Scenario: Refuse a membership invitation issued to another person
      Given a company membership invitation identifies an intended recipient email address
      And a person is signed in with a different verified email address
      When the person attempts to accept the invitation
      Then membership acceptance is refused
      And the person is instructed to sign in with the invited email address
      And no membership is created

  @IT-68R6
  Rule: Customer acquisition invitations and company membership invitations have different purposes


    @IT-68R6S1
    Scenario: Use a customer acquisition invitation
      Given a prospective customer received an invitation offering a new customer account
      When the customer provides onboarding information
      Then the customer may establish a solo or company customer account
      And introductory credits are governed by the customer acquisition offer
      And the invitation does not authorize membership in an unrelated existing company account

    @IT-68R6S2
    Scenario: Use a company membership invitation
      Given a person received an invitation to join an existing company customer account
      When the person provides onboarding information
      Then onboarding identifies that existing company account
      And the invitation authorizes only the offered membership
      And the invitation does not establish eligibility for a new-customer introductory grant

  @IT-68R7
  Rule: Account creation does not require payment information


    @IT-68R7S1
    Scenario Outline: Complete onboarding without payment details
      Given a person has supplied all required information for "<relationship>"
      And the person has satisfied the applicable onboarding requirements
      When the person completes onboarding without supplying payment details
      Then onboarding can complete
      And no payment card or bank account information is required

      Examples:
        | relationship                              |
        | Establish a solo customer account         |
        | Establish a company customer account      |
        | Join an existing company customer account |

  @IT-68R8
  Rule: Onboarding information is not exposed to other customers
  Rule: Accepted onboarding information is durable and traceable


    @IT-68R8S1
    Scenario: Preserve accepted information across a restart
      Given a person has successfully completed onboarding
      When the application server restarts
      And the person signs in again
      Then the accepted human-user information remains available
      And the customer account and authorized memberships remain available
      And the person is not required to repeat completed onboarding

    @IT-68R8S2
    Scenario: Record who established an account or accepted membership
      When a person successfully completes onboarding
      Then an audit record identifies the UAD user
      And the record identifies the affected customer account
      And the record identifies whether the person established an account or joined one
      And the record identifies when onboarding completed