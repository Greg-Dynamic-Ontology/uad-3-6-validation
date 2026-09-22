Feature: Build governed validation constraints at scale
  As an OTDD constraint-development process
  I want governed constraints to be constructed and verified in repeatable batches
  So that large governed constraint sets can be implemented efficiently
  without sacrificing test-first development, traceability, or governed meaning

  Background:
    Given a governed source contains multiple constraint requirements
    And each source constraint has a governed source identity
    And the Logical Schema Model represents the governed schema vocabulary
    And constraint construction proceeds through independently verifiable stages

  # IT-33 — Construct governed constraints through a repeatable stage-batched process

  @IT-33R1
  Rule: Process governed constraints in bounded batches through each construction stage before advancing the batch
    @IT-33R1S1
    Scenario: Process a batch at a constraint-construction stage
      Given a set of constraints is eligible for a construction stage
      When that construction stage is executed
      Then each eligible constraint is processed at that stage
      And each successfully processed constraint is eligible for verification
      And a constraint that cannot be processed is identified as an exception
      And an exception does not prevent other eligible constraints from being processed

  @IT-33R2
  Rule: Prove expected behavior before generating the artifact that satisfies it

    @IT-33R2S1
    Scenario: Establish a RED state before implementation
      Given a constraint is eligible for a construction stage
      And the expected result of that stage can be stated as executable tests
      When the tests for that stage are generated
      And the tests are executed before the required artifact is generated
      Then the tests fail for the absence of the required artifact or behavior
      And the failed tests establish the expected behavior for that stage

    @IT-33R2S2
    Scenario: Establish a GREEN state after implementation
      Given a constraint has established the expected RED state for a construction stage
      When the required artifact is generated
      And the tests for that stage are executed again
      Then the tests pass when the generated artifact satisfies the expected behavior
      And the constraint is eligible to advance to the next construction stage

  @IT-33R3
  Rule: Preserve governed knowledge throughout constraint construction

    @IT-33R3S1
    Scenario: Maintain traceability through generated representations
      Given a governed source constraint is being constructed
      When representations of that constraint are generated
      Then the governed source identity remains traceable
      And the normalized constraint identity remains traceable
      And source provenance remains traceable
      And generated executable representations remain traceable to the normalized constraint

    @IT-33R3S2
    Scenario: Do not replace governed knowledge with implementation-specific knowledge
      Given a governed constraint has established identity and meaning
      When an executable representation is generated
      Then the executable representation implements the governed constraint
      And implementation-specific identity does not replace governed identity
      And implementation-specific structure does not become the source of governed meaning

  @IT-33R4
  Rule: Classify recurring constraint behavior before generating repeated implementations

    @IT-33R4S1
    Scenario: Reuse an established constraint behavior
      Given multiple governed constraints exhibit the same validation behavior
      And that behavior has an established implementation pattern
      When those constraints reach the implementation stage
      Then the established behavior pattern is reused
      And constraint-specific governed knowledge is supplied to that pattern
      And each generated implementation remains traceable to its governed constraint

    @IT-33R4S2
    Scenario: Identify a previously unknown constraint behavior
      Given a governed constraint cannot be represented by an established behavior pattern
      When its behavior is classified
      Then the constraint is identified as requiring a new behavior pattern
      And an existing behavior pattern is not modified merely to force the constraint into it
      And the constraint does not advance until the new behavior is understood and governed

  @IT-33R5
  Rule: Isolate exceptions without stopping production of understood constraints

    @IT-33R5S1
    Scenario: Route an unresolved constraint for review
      Given a constraint cannot complete its current construction stage
      When the failure is evaluated
      Then the constraint is placed in an exception set
      And the failed construction stage is recorded
      And the reason for the exception is recorded
      And successfully processed constraints remain eligible to continue

    @IT-33R5S2
    Scenario: Resume construction after an exception is resolved
      Given a constraint is in an exception set
      And the knowledge required to resolve the exception has been supplied
      When the constraint is processed again
      Then processing resumes from the unresolved construction stage
      And previously verified stages do not need to be reconstructed unless their governed knowledge changed

  @IT-33R6
  Rule: Complete each governed constraint through the required OTDD knowledge-construction stages

    @IT-33R6S1
    Scenario: Advance a constraint through the construction process
      Given a governed constraint has been captured from its authoritative source
      When the constraint completes the OTDD construction process
      Then its normalized governed constraint representation is verified
      And its Logical Schema binding is verified
      And its applicable context is verified
      And its validation behavior is verified
      And its Instance RDF binding is verified
      And its executable SHACL representation is verified
      And its governed report finding behavior is verified

  @IT-33R7
  Rule: Project SHACL validation results into governed validation findings

    @IT-33R7S1
    Scenario: Produce a governed finding from a SHACL violation
      Given SHACL validation has produced a validation result
      And the validation result identifies the SHACL shape that produced it
      And the SHACL shape identifies the governed constraint it implements
      And the governed constraint graph contains the meaning and provenance of that constraint
      When the validation result is projected into a governed validation finding
      Then the finding identifies the governed constraint
      And the finding identifies the governed source constraint
      And the finding identifies the UMDP rule
      And the finding reports the governed severity
      And the finding reports the governed violation kind
      And the finding identifies the focus of the violation
      And the finding remains traceable to the SHACL validation result

    @IT-33R7S2
    Scenario: Produce no governed finding when SHACL reports no violation
      Given SHACL validation produces no validation result for a governed constraint
      When validation findings are projected
      Then no governed validation finding is produced for that constraint

  @IT-33R8
  Rule: Scale constraint-production batches logarithmically as confidence grows

    @IT-33R8S1
    Scenario: Increase the batch size after successful processing
      Given the current constraint-production batch has completed successfully
      And the regression suite remains green
      And unresolved exceptions do not indicate a systemic failure
      When the next constraint-production batch is started
      Then the batch size may increase logarithmically
      And the increased batch tests the ability of the process to operate at greater scale

    @IT-33R8S2
    Scenario: Do not increase scale when the current batch exposes systemic problems
      Given the current constraint-production batch exposes a systemic failure
      When the batch results are reviewed
      Then the next batch is not started at a larger scale
      And the constraint-production process is corrected
      And the affected batch is successfully verified before scaling continues
# Initial UAD 3.6 scaling schedule:
#
#   B1     C1          1 constraint
#   B2     C2-C3       2 constraints
#   B3     C4-C7       4 constraints
#   B4     C8-C15      8 constraints
#   B5     C16-C31    16 constraints
#   B6     C32-C63    32 constraints
#   B7     C64-C127   64 constraints
#   B8     C128-C255 128 constraints
#   B9     C256-C511 256 constraints
#   B10    C512-C730 219 constraints
