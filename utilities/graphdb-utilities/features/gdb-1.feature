@GDB-1
Feature: Provision and verify a GraphDB repository
  As an authorized application operator
  I want a reusable utility to provision and verify a GraphDB repository
  So that applications can use a durable RDF store with SHACL validation

  # GDB features use an independent numbering sequence.
  # Rule and scenario identifiers follow GDB-1R1 and GDB-1R1S1.
  # This utility contains no application-specific vocabulary or business rules.
  # Applications supply repository configuration and SHACL shapes.
  # Provisioning occurs per environment, not per customer.
  # Repository creation does not start or install the GraphDB server.
  # A transaction commit means a GraphDB transaction commit.
  # Git commits and GitHub pushes are outside this feature.
  # Repository deletion, migration, and shape upgrades are outside this feature.

  Background:
    Given the operator has supplied the GraphDB server URL
    And the operator has supplied a repository ID
    And the operator has supplied the required repository configuration
    And the operator has supplied a versioned SHACL shape set
    And the operator has supplied the data-graph scope for SHACL validation
    And any required credentials are supplied securely

  @GDB-1R1
  Rule: The utility provisions a missing repository

    @GDB-1R1S1
    Scenario: Create a repository with SHACL validation
      Given the GraphDB server is reachable
      And the operator is authorized to create repositories
      And the requested repository does not exist
      When the operator runs repository setup
      Then the utility creates the requested repository
      And SHACL validation is enabled
      And the repository configuration matches the supplied requirements
      And existing repositories remain unchanged

    @GDB-1R1S2
    Scenario: Report an unreachable GraphDB server
      Given the GraphDB server is unreachable
      When the operator runs repository setup
      Then setup reports that it cannot connect to the configured server
      And setup returns a failure result
      And setup does not report the repository as ready

    @GDB-1R1S3
    Scenario: Report insufficient provisioning permissions
      Given the GraphDB server is reachable
      And the operator is not authorized to create repositories
      And the requested repository does not exist
      When the operator runs repository setup
      Then setup reports the authorization failure
      And setup returns a failure result
      And setup does not report the repository as ready

  @GDB-1R2
  Rule: Repository readiness requires the supplied SHACL shapes

    @GDB-1R2S1
    Scenario: Install the supplied shape set
      Given the requested repository exists with SHACL validation enabled
      And the repository has no installed application shape set
      And the supplied shape set is valid
      When the utility installs the supplied shape set
      Then the shapes are durably stored in the repository
      And the shapes apply to the configured data-graph scope
      And the installed shape version and content digest are recorded
      And the utility can retrieve the installed shapes
      And the retrieved shape graph is equivalent to the supplied shape graph

    @GDB-1R2S2
    Scenario: Reject an invalid shape set
      Given the supplied shape set cannot be parsed or accepted for SHACL validation
      When the operator runs repository setup
      Then setup reports the shape-set error
      And setup returns a failure result
      And no partial shape-set installation is committed
      And setup does not report the repository as ready

    @GDB-1R2S3
    Scenario: Report failure after repository creation
      Given setup has created the requested repository
      And installation of the supplied shape set fails
      When setup reports its result
      Then the result identifies the repository as created but not ready
      And the result identifies the failed setup step
      And the utility does not delete the repository
      And setup returns a failure result

  @GDB-1R3
  Rule: Repeated setup preserves existing data and configuration

    @GDB-1R3S1
    Scenario: Repeat setup for a correctly provisioned repository
      Given the requested repository is already correctly provisioned
      And its installed shape version and content digest match the supplied shape set
      When the operator runs repository setup again
      Then setup succeeds
      And the repository is not replaced
      And existing RDF data remains unchanged
      And the installed shapes remain unchanged
      And no duplicate setup metadata is created

    @GDB-1R3S2
    Scenario: Detect incompatible repository configuration
      Given the requested repository already exists
      And its configuration does not meet the supplied requirements
      When the operator runs repository setup
      Then setup identifies the incompatible settings
      And setup returns a failure result
      And the repository configuration remains unchanged
      And existing RDF data remains unchanged
      And the utility does not delete or recreate the repository

    @GDB-1R3S3
    Scenario: Detect a different installed shape set
      Given the requested repository already contains an application shape set
      And its version or content digest differs from the supplied shape set
      When the operator runs repository setup
      Then setup reports the shape-set mismatch
      And setup returns a failure result
      And existing shapes and RDF data remain unchanged
      And setup does not automatically upgrade or replace the shapes

  @GDB-1R4
  Rule: Verification demonstrates persistence and SHACL enforcement

    @GDB-1R4S1
    Scenario: Verify a conforming dataset
      Given the repository configuration and installed shapes meet the supplied requirements
      And the operator supplies a conforming verification dataset
      And an isolated verification graph is within the configured validation scope
      When the utility commits the verification dataset to that graph
      Then the GraphDB transaction succeeds
      And a subsequent read retrieves an equivalent RDF graph
      And resource identifiers, relationships, and literal datatypes are preserved
      And the utility removes its verification data after the check
      And pre-existing RDF data remains unchanged

    @GDB-1R4S2
    Scenario: Verify rejection of a nonconforming dataset
      Given the repository configuration and installed shapes meet the supplied requirements
      And the operator supplies a dataset that violates an identified active shape
      And an isolated verification graph is within the configured validation scope
      When the utility attempts to commit that dataset to the verification graph
      Then GraphDB rejects the transaction because of the shape violation
      And none of the attempted dataset is committed
      And the utility reports the validation failure as the expected verification outcome
      And pre-existing RDF data remains unchanged

    @GDB-1R4S3
    Scenario: Detect missing SHACL enforcement
      Given the operator supplies a dataset that violates an identified active shape
      When the utility attempts to commit that dataset within the configured validation scope
      And GraphDB accepts the transaction
      Then verification fails
      And the utility reports that the expected SHACL rejection did not occur
      And the utility removes its verification data
      And the repository is not reported as ready

    @GDB-1R4S4
    Scenario: Report unsuccessful verification cleanup
      Given the utility has written verification data
      And removal of that verification data fails
      When the utility reports its verification result
      Then verification returns a failure result
      And the result identifies the graph requiring cleanup
      And the repository is not reported as ready

  @GDB-1R5
  Rule: Applications can invoke the utility and interpret its result

    @GDB-1R5S1
    Scenario: Report a ready repository
      Given repository setup and all required verification checks succeed
      And verification cleanup succeeds
      When the utility returns its result
      Then the result reports success
      And it identifies the server URL and repository ID
      And it identifies the installed shape version and content digest
      And it identifies the verified data-graph scope
      And it reports the repository as ready
      And it contains no credentials or authentication secrets

    @GDB-1R5S2
    Scenario: Invoke setup without interactive prompts
      Given an application supplies all required setup and verification inputs
      When the application invokes the utility
      Then the utility requires no interactive input
      And it returns a machine-readable result
      And the result distinguishes success from failure
      And a failure result identifies the failed step and available diagnostic details
      And diagnostic output contains no credentials or authentication secrets