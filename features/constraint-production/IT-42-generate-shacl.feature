Feature: 6 Generate SHACL from governed constraint knowledge
  As the governed constraint-production process
  I want a SHACL-generation agent to derive executable SHACL from verified governed constraint knowledge
  So that validation execution implements the governed requirement without becoming the source of its meaning

  Background:
    Given a normalized governed constraint is available
    And the normalized constraint is bound to a governed Logical Schema resource
    And the governed applicable context has been resolved
    And the governed validation behavior has been classified
    And the governed Instance RDF binding has been established
    And the SHACL-generation agent has an explicit input, output, and error contract

  # IT-42R1 — Generate an executable SHACL representation

  @IT-42R1
  Rule: Generate SHACL only from verified governed constraint knowledge

    @IT-42R1S1
    Scenario: Generate one SHACL representation for a governed constraint
      Given the governed validation behavior has an established SHACL implementation pattern
      And the governed Instance RDF binding identifies the RDF representation to be validated
      And exactly one SHACL representation is determined by the governed behavior and Instance RDF binding
      When the SHACL-generation agent executes
      Then one executable SHACL representation is produced
      And the SHACL representation identifies the governed constraint it implements
      And the SHACL target is derived from the governed applicable context
      And the SHACL path is derived from the governed Instance RDF binding
      And the SHACL constraint components are derived from the governed validation behavior
      And the SHACL representation preserves the governed requirement message where required
      And the SHACL representation remains traceable to the governed source constraint
      And the SHACL representation is written to its governed project location
      And the SHACL representation is available to validation execution

  # IT-42R2 — Keep executable SHACL subordinate to governed knowledge

  @IT-42R2
  Rule: SHACL implements governed constraint knowledge but does not define it

    @IT-42R2S1
    Scenario: Preserve governed meaning independently of generated SHACL
      Given a governed constraint can be represented as executable SHACL
      When the SHACL-generation agent produces the SHACL representation
      Then the normalized governed constraint remains the source of requirement meaning
      And the governed validation behavior remains the source of validation semantics
      And the governed applicable context remains the source of applicability
      And the governed Instance RDF binding remains the source of RDF implementation binding
      And SHACL-specific structures do not replace governed knowledge
      And the generated SHACL explicitly identifies the governed constraint it implements

  # IT-42R3 — Reuse established SHACL implementation patterns

  @IT-42R3
  Rule: Reuse a governed SHACL implementation pattern for recurring validation behavior

    @IT-42R3S1
    Scenario: Generate constraint-specific SHACL from an established behavior pattern
      Given more than one governed constraint uses the same established validation behavior
      And that validation behavior has an established SHACL implementation pattern
      When the SHACL-generation agent generates SHACL for each constraint
      Then the same governed implementation pattern is reused
      And each generated SHACL representation retains its own governed constraint identity
      And each generated SHACL representation uses its own governed applicable context
      And each generated SHACL representation uses its own governed Instance RDF binding
      And constraint-specific governed knowledge is not replaced by shared implementation knowledge

  # IT-42R4 — Reject unsupported or ambiguous SHACL generation

  @IT-42R4
  Rule: Do not invent executable SHACL when governed knowledge does not determine an implementation

    @IT-42R4S1
    Scenario: Reject a constraint whose validation behavior has no governed SHACL implementation pattern
      Given the governed validation behavior has been classified
      And no governed SHACL implementation pattern exists for that behavior
      When the SHACL-generation agent executes
      Then no SHACL representation is produced for that constraint
      And an exception is produced
      And the exception identifies the normalized constraint
      And the exception identifies the SHACL-representation stage
      And the exception identifies the unsupported governed validation behavior
      And the agent does not invent a SHACL implementation pattern
      And the exception is eligible to be written to the Batch Results Graph
      And the constraint is routed for review

    @IT-42R4S2
    Scenario: Reject a constraint when more than one incompatible SHACL representation is permitted
      Given the governed validation behavior has an established implementation pattern
      And more than one incompatible SHACL representation is consistent with the governed knowledge
      When the SHACL-generation agent executes
      Then no SHACL representation is selected merely because it is statistically plausible
      And no SHACL representation is produced for that constraint
      And an exception is produced
      And the exception records the incompatible implementation alternatives
      And the constraint is routed for review

  # IT-42R5 — Satisfy the SHACL-generation agent contract

  @IT-42R5
  Rule: The SHACL-generation agent behaves as a bounded worker

    @IT-42R5S1
    Scenario: Return only contracted output or a contracted exception
      Given the SHACL-generation agent receives verified governed behavior and Instance RDF binding knowledge
      When the SHACL-generation agent completes its work
      Then it returns an executable SHACL representation or a SHACL-generation exception
      And it does not change normalized governed constraint meaning
      And it does not change the governed Logical Schema binding
      And it does not change the governed applicable context
      And it does not change the governed validation behavior
      And it does not change the governed Instance RDF binding
      And it does not generate report findings
