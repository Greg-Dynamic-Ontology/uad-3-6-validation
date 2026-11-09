@IT-64
Feature: Persist and validate customer RDF data
  As the UAD application
  I want to persist customer RDF data in GraphDB with SHACL validation
  So that customer-account operations use durable, conforming data

  # Establishes the persistence and validation foundation for IT-65.
  # Existing IT-44 account and permission requirements remain in force.
  # WorkOS manages authentication; UAD manages customer accounts and memberships.
  # GraphDB holds the authoritative customer RDF dataset.
  # Version-controlled Turtle files define the vocabulary, SHACL shapes,
  # and test fixtures; they are not a second operational customer store.
  # Customer lifecycle behavior and permissions are specified in IT-65.
  # Payment details, validation reports, and retention policies are outside
  # this feature.

  Background:
    Given a GraphDB repository is configured for customer RDF data
    And SHACL validation is enabled for that repository
    And the approved customer vocabulary and SHACL shapes are version controlled
    And the repository uses an identified version of those shapes
    And customer-data writes occur within transactions
    And each requested change identifies the acting UAD user or system process

  @IT-64R1
  Rule: Customer RDF data is durably stored in GraphDB

    @IT-64R1S1
    Scenario: Persist and retrieve a conforming customer dataset
      Given a customer RDF dataset that conforms to the active SHACL shapes
      When UAD commits that dataset to GraphDB
      Then the transaction succeeds
      And UAD can retrieve the committed customer data
      And the retrieved RDF graph is equivalent to the committed RDF graph
      And resource identifiers, relationships, and literal datatypes are preserved

    @IT-64R1S2
    Scenario: Retrieve committed data after reconnecting
      Given UAD has committed a conforming customer RDF dataset
      When UAD closes its connection to GraphDB
      And UAD establishes a new connection to the same repository
      Then UAD can retrieve the committed customer data
      And the customer resource identifiers are unchanged

  @IT-64R2
  Rule: SHACL validation protects every customer-data commit

    @IT-64R2S1
    Scenario: Accept a change that leaves the customer dataset conforming
      Given the stored customer RDF dataset conforms to the active SHACL shapes
      And a proposed change leaves the resulting dataset conforming
      When UAD commits the proposed change
      Then the transaction succeeds
      And the changed data is available to subsequent reads

    @IT-64R2S2
    Scenario Outline: Reject a change that violates an enforced shape
      Given the stored customer RDF dataset conforms to the active SHACL shapes
      And a proposed change introduces <violation>
      When UAD attempts to commit the proposed change
      Then SHACL validation rejects the transaction
      And none of the proposed changes are committed
      And the previously committed customer dataset is unchanged

      Examples:
        | violation                                                   |
        | a missing property required by an active shape               |
        | a literal with a datatype prohibited by an active shape      |
        | more values for a property than an active shape permits      |
        | a relationship target that fails an active shape constraint  |

    @IT-64R2S3
    Scenario: Report an actionable SHACL validation failure
      Given a proposed customer-data change violates an active SHACL shape
      When UAD attempts to commit the proposed change
      Then UAD receives a SHACL validation report
      And the report identifies the nonconforming focus node
      And the report identifies the violated constraint
      And the report identifies the property path when applicable
      And UAD associates the failure with the attempted change
      And UAD does not report the change as successful

    @IT-64R2S4
    Scenario: Reject deletion that would leave invalid customer relationships
      Given the stored customer RDF dataset conforms to the active SHACL shapes
      And a stored relationship requires its target to satisfy an active shape
      When UAD attempts to delete data required for that target to conform
      Then SHACL validation rejects the transaction
      And the relationship and its target remain unchanged

  @IT-64R3
  Rule: Related customer-data changes are atomic

    @IT-64R3S1
    Scenario: Commit related resources together
      Given a proposed transaction creates a customer account and its owner membership
      And the resulting customer dataset conforms to the active SHACL shapes
      When UAD commits the transaction
      Then the account and membership are both committed
      And subsequent readers cannot observe a partially committed transaction

    @IT-64R3S2
    Scenario: Roll back all changes when one related resource is invalid
      Given a proposed transaction changes multiple customer resources
      And one of those changes violates an active SHACL shape
      When UAD attempts to commit the transaction
      Then the entire transaction is rejected
      And every affected resource retains its previously committed state

    @IT-64R3S3
    Scenario: Roll back a transaction that fails before commit
      Given UAD has started a customer-data transaction
      And the transaction contains uncommitted changes
      When an operation fails before the commit is requested
      Then UAD rolls back the transaction
      And none of its changes are available to subsequent reads

  @IT-64R4
  Rule: Concurrent changes preserve validated customer data

    @IT-64R4S1
    Scenario: Reject conflicting changes that would jointly violate a shape
      Given two transactions begin from the same conforming customer dataset
      And each proposed change would conform when applied alone
      But committing both changes would violate an active SHACL shape
      When both transactions attempt to commit
      Then both conflicting changes cannot be committed
      And the resulting customer dataset conforms to the active SHACL shapes
      And UAD receives a failure result for each rejected transaction

    @IT-64R4S2
    Scenario: Reject an update based on an obsolete resource version
      Given two administrators have read the same version of a customer resource
      And the first administrator's update has been committed
      When UAD attempts the second administrator's update using the earlier version
      Then UAD rejects the stale update as a conflict
      And the first administrator's committed changes are preserved
      And UAD indicates that the resource must be refreshed before retrying

  @IT-64R5
  Rule: Customer-data changes are attributable

    @IT-64R5S1
    Scenario: Record the actor and validation version for a committed change
      Given a proposed customer-data change conforms to the active SHACL shapes
      When UAD commits the change
      Then a durable change record identifies the acting UAD user or system process
      And the record identifies the affected customer resources
      And the record includes the change time and operation
      And the record identifies the SHACL shape version used
      And the change and its attribution record are committed atomically

    @IT-64R5S2
    Scenario: Reject a change without an attributable actor
      Given a proposed customer-data change has no identified actor
      When UAD receives the change request
      Then UAD rejects the request
      And the stored customer dataset is unchanged

  @IT-64R6
  Rule: Shape changes cannot silently invalidate stored customer data

    @IT-64R6S1
    Scenario: Activate a compatible shape version
      Given a proposed approved SHACL shape version
      And the stored customer dataset conforms to that version
      When UAD activates the proposed shape version
      Then the repository enforces that version for subsequent commits
      And the active shape version is identifiable

    @IT-64R6S2
    Scenario: Reject an incompatible shape version
      Given a proposed SHACL shape version
      And existing customer data violates that version
      When UAD attempts to activate the proposed shape version
      Then activation is rejected with a validation report
      And the previously active shapes remain in force
      And the stored customer dataset is unchanged

  @IT-64R7
  Rule: Persistence failures are reported without claiming success

    @IT-64R7S1
    Scenario: Report an unavailable repository
      Given the customer GraphDB repository is unavailable
      When UAD attempts to persist a customer-data change
      Then UAD reports that persistence is unavailable
      And UAD does not report the change as committed
      And UAD does not substitute a local Turtle file as the operational store

    @IT-64R7S2
    Scenario: Report an uncertain commit outcome
      Given UAD has submitted a customer-data transaction for commit
      When the connection is lost before UAD receives the commit result
      Then UAD reports that the commit outcome is unconfirmed
      And UAD does not claim either success or rollback
      And UAD reconciles the transaction outcome before retrying the change

