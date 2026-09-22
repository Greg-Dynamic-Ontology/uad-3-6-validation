Feature: 4 Classify governed validation behavior
  As the governed constraint-production process
  I want a validation-behavior agent to classify the behavior required by each context-resolved constraint
  So that executable representations can be derived from governed meaning rather than invented independently

  Background:
    Given a normalized governed constraint is available
    And the normalized constraint is bound to a governed Logical Schema resource
    And the governed applicable context has been resolved
    And the governed requirement and violation condition are available
    And the validation-behavior agent has an explicit input, output, and error contract

  # IT-40R1 — Reuse established governed validation behavior

  @IT-40R1
  Rule: Classify a constraint using an established behavior when governed knowledge determines the behavior

    @IT-40R1S1
    Scenario: Classify a constraint using one established validation behavior
      Given the governed requirement and violation condition match one established validation behavior
      When the validation-behavior agent executes
      Then the constraint is classified with that established validation behavior
      And the behavior classification preserves the normalized constraint identity
      And the behavior classification preserves the governed requirement
      And the behavior classification preserves the governed violation condition
      And the behavior classification preserves the governed applicable context
      And the behavior classification remains traceable to the governed source constraint
      And the established behavior identity is reused
      And the behavior classification is available to downstream constraint-production agents

  # IT-40R2 — Preserve governed meaning independently of executable representation

  @IT-40R2
  Rule: Validation behavior expresses governed meaning rather than SHACL implementation structure

    @IT-40R2S1
    Scenario: Preserve governed validation behavior independently of SHACL
      Given a governed constraint has been classified with an established validation behavior
      When the validation-behavior agent records the classification
      Then the behavior is stated independently of SHACL
      And the governed requirement remains authoritative
      And the governed violation condition remains authoritative
      And SHACL predicates do not become the source of governed behavior meaning
      And more than one executable representation may implement the same governed behavior

  # IT-40R3 — Identify behavior not yet governed by an established classification

  @IT-40R3
  Rule: Do not force a constraint into an established behavior when governed knowledge does not support that classification

    @IT-40R3S1
    Scenario: Report an unknown validation behavior
      Given the governed requirement and violation condition do not match any established validation behavior
      When the validation-behavior agent executes
      Then no established validation behavior is assigned to the constraint
      And an exception is produced
      And the exception identifies the normalized constraint
      And the exception identifies the validation-behavior stage
      And the exception preserves the governed requirement and violation condition
      And the exception identifies that a new behavior classification may be required
      And the agent does not alter the governed requirement to fit an existing behavior
      And the exception is eligible to be written to the Batch Results Graph
      And the constraint is routed for review

    @IT-40R3S2
    Scenario: Reject an ambiguous validation behavior classification
      Given the governed requirement and violation condition are consistent with more than one incompatible established validation behavior
      When the validation-behavior agent executes
      Then no behavior is selected merely because it is statistically plausible
      And no validation behavior classification is produced for that constraint
      And an exception is produced
      And the exception records the candidate governed behaviors
      And the constraint is routed for review

  # IT-40R4 — Satisfy the validation-behavior agent contract

  @IT-40R4
  Rule: The validation-behavior agent behaves as a bounded worker

    @IT-40R4S1
    Scenario: Return only contracted output or a contracted exception
      Given the validation-behavior agent receives a context-resolved governed constraint
      When the validation-behavior agent completes its work
      Then it returns a governed validation behavior classification or a validation-behavior exception
      And it does not change normalized governed constraint meaning
      And it does not change the governed Logical Schema binding
      And it does not change the governed applicable context
      And it does not generate Instance RDF bindings
      And it does not generate SHACL
      And it does not generate report findings
