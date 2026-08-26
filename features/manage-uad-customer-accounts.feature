@otdd @uad @accounts @multi-tenant
Feature: Manage UAD customer accounts and their users

As a customer using the UAD report-validation service
I want people and software clients to act within a customer account
So that reports, validation cycles, credits, billing, permissions, and audit history have an unambiguous owner

Background:
Given the UAD customer-account service is available

Rule: Represent phone numbers consistently across forms and services

@otdd-phone-representation-s-01 @phone-number @normalization @forms
Scenario Outline: Normalize a phone number submitted by a form
Given a person enters the formatted phone number <form value> on a form
When the form submits the phone number to the service
Then the service normalizes the phone number to the internal value <internal value>
And the internal value contains exactly 11 characters
And every character in the internal value is a decimal digit from "0" through "9"
And no formatting characters are retained in the internal value

Examples:
| form value          | internal value |
| "+1-999-999-9999" | "19999999999" |
| "+1-999-999-9977" | "19999999977" |

@otdd-phone-representation-s-02 @phone-number @validation @forms
Scenario Outline: Reject a form value that cannot become an internal phone number
Given a person enters <form value> as a phone number on a form
When the form submits the phone number to the service
Then the phone number is rejected
And no human-user identity is looked up or created
And the form explains that a phone number with country calling code is required

Examples:
| form value                              |
| a value containing fewer than 11 digits |
| a value containing more than 11 digits  |
| a value containing alphabetic characters |

@otdd-phone-representation-s-03 @phone-number @forms @presentation
Scenario: Format an internal country-code-1 phone number for a form
Given the service has the internal phone number "19999999999"
When a form displays the phone number
Then the form displays "+1-999-999-9999"
And the formatted value is not stored as the internal phone number

@otdd-phone-representation-s-04 @phone-number @internal-representation
Scenario: Use only the numeric representation inside the service
Given a form has submitted a valid phone number
When the service stores, looks up, compares, or evaluates the phone number
Then the service uses an 11-character numeric string
And the internal value contains no plus sign, hyphen, space, or parentheses
And a formatted phone number appears only on a form

Rule: Treat a verified phone number as the identity of a human user

@otdd-user-identity-s-01 @user-identity @phone-number
Scenario Outline: Determine the registration state of a human user by phone number
Given a person's form submission has been normalized to an 11-character numeric phone number
And the internal phone number <registration condition>
When the service looks up the internal phone number
Then the person is treated as <user state>
And no name, email address, or customer-account membership is required to make that determination

Examples:
| registration condition                  | user state       |
| identifies an existing human user       | an existing user |
| does not identify an existing human user | a new user       |

@otdd-user-identity-s-02 @user-identity @phone-number @verification
Scenario: Verify control of a phone number before activating a human user
Given a person's form submission has been normalized to an 11-character numeric phone number
And the internal phone number does not identify an existing human user
When the person proves control of the phone number
Then the service creates one human-user identity for the internal phone number
And the phone number is marked as verified
And alternate formatting of the same international phone number does not create another user
And possession of the phone number is verified separately from authorization within a customer account

Rule: Determine operating mode from the user phone number

@otdd-user-mode-s-01 @phone-number @country-code @demo-mode
Scenario: Place a user with a non-1 country calling code into Demo mode
Given a human user has an 11-character numeric internal phone number
And the recognized country calling code in the phone number is other than "1"
When the service determines the user's operating mode
Then the user's operating mode is Demo mode
And the Demo-mode service limitations apply
And the mode selection does not bypass phone verification or account authorization

@otdd-user-mode-s-02 @phone-number @developer-mode
Scenario: Place the designated developer phone number into Developer mode
Given a human user has the internal phone number "19999999977"
When the service determines the user's operating mode
Then the user's operating mode is Developer mode
And the exact developer-number rule takes precedence over the general country-code rule
And no other phone number enables Developer mode
And the mode selection does not bypass phone verification or account authorization

@otdd-user-mode-s-03 @phone-number @country-code @standard-mode
Scenario: Do not force other country-code-1 users into Demo or Developer mode
Given a human user has an 11-character numeric internal phone number with country calling code "1"
And the internal phone number is not "19999999977"
When the service determines the user's operating mode
Then the country-code rule does not place the user into Demo mode
And the developer-number rule does not place the user into Developer mode
And the user's operating mode is determined by the standard account policy

Rule: Create every customer account with an accountable owner

@otdd-account-s-01 @account-creation @owner
Scenario: Create a customer account with its first owner
Given a person has a verified 11-character numeric internal phone number
And the person is eligible to create a customer account
When the person creates the customer account
Then the service assigns a unique customer account identifier
And the customer account becomes the ownership and billing boundary
And the person becomes the first active owner of the account
And the account creation and owner assignment are recorded in the audit history

@otdd-account-s-02 @solo-appraiser @account-creation
Scenario: Represent a solo appraiser as a customer account with one user
Given a solo appraiser wants to use the validation service
When the solo appraiser registers
Then one customer account is created
And the solo appraiser is its first owner
And the account uses the same ownership, billing, and audit model as a multi-user organization
And no separate individual-account model is required

Rule: Add people to customer accounts through explicit invitations

@otdd-account-s-03 @invitation @membership
Scenario: Invite a user to a customer account
Given an active customer account has an owner
And a person is not yet a member of the account
When the owner enters the person's formatted phone number on the invitation form and assigns an allowed role
Then a pending membership invitation is created
And the invitation identifies the intended human user, customer account, and proposed role
And the invitation stores the phone number as an 11-character numeric string
And the invited person cannot act as a member before accepting the invitation
And the invitation is recorded in the account audit history

@otdd-account-s-04 @invitation @membership
Scenario: Accept an invitation to join a customer account
Given a person has a valid pending membership invitation
When the person accepts the invitation
Then an active membership is created for that person and customer account
And the membership receives the invited role
And the invitation cannot be accepted a second time
And the acceptance is recorded in the account audit history

  @IT-16R1
Rule: Authorize customer actions according to membership role

@otdd-account-s-05 @IT-16R1S1
Scenario Outline: Authorize a user according to the assigned role
Given a user has an active <role> membership in a customer account
When the user attempts to <activity>
Then the activity is <decision>
And the authorization decision is evaluated within that customer account

Examples:
| role                  | activity                                      | decision |
| owner                 | manage membership and account closure         | allowed  |
| billing administrator | purchase credits and view financial history   | allowed  |
| validator             | submit reports and manage validation cycles   | allowed  |
| reviewer              | view reports, findings, and cycle histories   | allowed  |
| reviewer              | submit a report for a new validation cycle    | denied   |
| validator             | close the customer account                    | denied   |

@otdd-account-s-06 @@IT-16R1S2
Scenario: Require an owner to manage membership and account closure
Given a customer account is active
When a user without the owner role attemp ts to manage membership or close the account
Then the request is denied
And the customer account remains unchanged
And the denied request is recorded in the audit history

@otdd-account-s-07 @IT-16R1S3
Scenario: Allow a billing administrator to manage credits and financial history
Given a user is an active billing administrator of a customer account
When the user accesses account billing
Then the user can purchase validation credits
And the user can view credit balances and credit-ledger activity
And the user can view payment, refund, and invoice history for the account
And the user cannot use billing authority to gain access to another customer account

@otdd-account-s-08 @IT-16R1S4
Scenario: Allow a validator to submit reports and manage validation cycles
Given a user is an active validator of a customer account
When the user submits a UAD appraisal report for validation
Then the report submission is scoped to that customer account
And any resulting validation cycle is owned by that customer account
And the user is recorded as the actor who submitted the report

@otdd-account-s-09 @IT-16R1S5
Scenario: Keep the reviewer role read-only
Given a user is an active reviewer of a customer account
When the user accesses reports, findings, and validation-cycle history
Then the user can view the information authorized for that account
But the user cannot create a validation cycle
And the user cannot modify reports, findings, credits, billing, or membership

  @IT-17R1
Rule: Preserve account records when membership changes

@otdd-account-s-10 @IT-17R1S1
Scenario: Remove a member without removing account records
Given a user has an active membership in a customer account
And the user previously performed actions for that account
When an owner removes the membership
Then the user can no longer act within the customer account
And reports, validation cycles, credits, billing records, and audit history remain owned by the account
And prior actions remain attributed to the removed user
And the membership removal is recorded in the audit history

@otdd-account-s-11 @IT-17R1S2
Scenario: Allow one person to belong to multiple customer accounts
Given a person has active memberships in two customer accounts
When the person selects one customer account as the active context
Then permissions are evaluated from the membership in the selected account
And reports, cycles, credits, and billing from the other account are not included
And switching account context does not transfer ownership between accounts

  @IT-18R1
Rule: Make customer-owned service resources belong to the customer account

@otdd-account-s-12 @IT-18R1S1
Scenario: Make validation credits belong to the customer account
Given a user purchases validation credits while acting in a customer account
When the payment completes and the credits are issued
Then the credits belong to the customer account
And the credits do not belong personally to the purchasing user
And removing the purchasing user's membership does not remove the credits
And credit use is attributed to the acting user or software client

@otdd-account-s-13 @IT-18R1S2
Scenario: Make reports and validation cycles belong to the customer account
Given a user or software client acts for a customer account
When it submits a report or opens a validation cycle
Then the report artifact belongs to the customer account
And the validation cycle belongs to the customer account
And membership changes do not transfer or remove that ownership
And access remains governed by account membership and retention policy

  @IT-19R1
Rule: Isolate customer accounts and attribute their actions

@otdd-account-s-14 @IT-19R1S1
Scenario: Isolate one customer account from another
Given a report, validation cycle, finding, credit entry, or billing record belongs to one customer account
When a user or software client acting for another account requests it
Then access is denied
And no protected account information is disclosed
And the protected record remains unchanged
And the denied access is recorded for security review

@otdd-account-s-15 @IT-19R1S2
Scenario: Attribute every material action to an actor and account
Given a human user or software client performs a material account action
When the action is accepted or denied
Then the audit record identifies the customer account
And the audit record identifies the acting user or software client
And the audit record identifies the action and its effective time
And the audit record identifies the affected resource when applicable
And later membership changes do not rewrite the actor attribution

  @IT-20R1
Rule: Give software clients separate credentials and scopes

@otdd-account-s-16 @IT-20R1S1
Scenario: Create a software client with separate credentials and scopes
Given an owner is authorized to manage software clients for a customer account
When the owner creates a software client
Then the software client receives an identity distinct from every human user
And its credentials are separate from human login credentials
And its permissions are limited to explicitly granted scopes
And its actions are attributed to the software-client identity
And its credentials do not grant access to another customer account

@otdd-account-s-17 @IT-20R1S2
Scenario: Revoke a software client's credentials
Given a software client has active credentials for a customer account
When an owner revokes the credentials
Then the software client can no longer authenticate with those credentials
And existing customer-account records remain unchanged
And the revocation is recorded in the audit history

  @IT-21R1
Rule: Preserve governed records throughout account suspension and closure

@otdd-account-s-18 @IT-21R1S1
Scenario: Suspend a customer account while preserving its records
Given a customer account is active
When an authorized administrative action suspends the account
Then users and software clients cannot open new validation cycles
And no new retail credit purchases are accepted
And existing reports, cycles, findings, credits, billing records, and audit history are preserved
And access required for authorized review or account resolution follows suspension policy
And the suspension is recorded in the audit history

@otdd-account-s-19 @IT-21R1S2
Scenario: Close a customer account without silently deleting governed records
Given a customer account is eligible for closure
When an owner completes the account-closure process
Then the customer account transitions to closed
And users and software clients cannot perform new operational activity
And reports, cycles, findings, billing records, and audit history are retained or disposed of according to policy
And unused credits and outstanding financial obligations are handled according to billing policy
And the closure is recorded in the audit history

  @IT-22R1-A
Rule: Apply centrally governed GSE constraints without weakening them

Given GSE constraint sets are centrally governed and versioned

  @IT-22R1S1
Scenario: Prevent a customer account from weakening governed GSE constraints
Given a customer account validates UAD appraisal reports
When an owner, user, or software client configures account preferences
Then the preferences cannot disable or weaken centrally governed applicable GSE constraints
And every validation result identifies the constraint-set versions applied


  @IT-23R1
Rule: Keep customer systems of record and GSE submissions outside the service boundary

  @IT-23R1S1
Scenario: Keep the customer responsible for its system of record and GSE submission
Given a report is owned by a customer account and passes validation
When the passing result is returned
Then the validation service does not modify the customer's system of record
And the validation service does not replace the customer's authoritative report
And the validation service does not submit the report to a GSE
And the acting customer account remains responsible for GSE submission
