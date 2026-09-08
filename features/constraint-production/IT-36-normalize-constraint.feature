Feature: 1 Normalize governed constraints
  As the governed constraint-production process
  I want a normalization agent to transform governed source rows into normalized constraint knowledge
  So that downstream agents receive a stable, traceable, implementation-independent constraint representation

  Background:
    Given a governed source constraint is available
    And the governed source constraint has a governed Unique ID
    And the governed source location is known
    And source provenance is available
    And the normalization agent has an explicit input, output, and error contract

  # IT-36R1 — Produce normalized governed constraint knowledge

  @IT-36R1
  Rule: Produce normalized constraint RDF from sufficient governed source knowledge

    @IT-36R1S1
    Scenario: Produce normalized RDF from a governed source constraint
      Given a governed source row contains the Unique ID
      And the governed source row contains the data point name
      And the governed source row contains the source rule identifier
      And the governed source row contains the requirement text
      And the governed source row contains the violation condition
      And the governed source row contains the severity
      And the governed source row contains the source context fields
      When the normalization agent executes
      Then a normalized governed constraint resource is produced
      And the normalized constraint preserves the governed Unique ID
      And the normalized constraint preserves the source rule identifier
      And the normalized constraint preserves the requirement text
      And the normalized constraint preserves the violation condition
      And the normalized constraint preserves the severity
      And the normalized constraint preserves the source context knowledge
      And the normalized constraint remains traceable to the governed source location
      And the normalized constraint remains traceable to its source provenance
      And the normalized constraint does not depend on a SHACL representation
      And the normalized constraint RDF is written to its governed project location

  # IT-36R2 — Preserve governed knowledge during normalization

  @IT-36R2
  Rule: Normalization must not replace governed source knowledge with implementation-specific knowledge

    @IT-36R2S1
    Scenario: Preserve governed meaning independently of implementation technology
      Given a governed source constraint can be normalized
      When the normalization agent produces the normalized constraint RDF
      Then governed source identity remains authoritative
      And governed source meaning remains authoritative
      And implementation-specific identifiers do not replace governed identifiers
      And implementation-specific structures do not become the source of governed meaning
      And no SHACL-specific knowledge is required to state the normalized constraint

  # IT-36R3 — Reject insufficient or ambiguous governed input

  @IT-36R3
  Rule: Do not invent normalized constraint knowledge when governed input is insufficient

    @IT-36R3S1
    Scenario: Reject a governed source row with insufficient required knowledge
      Given a governed source row is missing knowledge required by the normalization contract
      When the normalization agent executes
      Then no normalized governed constraint is produced for that row
      And an exception is produced
      And the exception identifies the governed source constraint when its identity is available
      And the exception identifies the normalization stage
      And the exception identifies the missing governed knowledge
      And the agent does not infer or invent a replacement value
      And the exception is eligible to be written to the Batch Results Graph

    @IT-36R3S2
    Scenario: Reject ambiguous governed source knowledge
      Given a governed source row contains more than one incompatible interpretation required for normalization
      When the normalization agent executes
      Then no interpretation is selected merely because it is statistically plausible
      And no normalized governed constraint is produced for that row
      And an exception is produced
      And the exception records the ambiguous governed knowledge
      And the constraint is routed for review

  # IT-36R4 — Satisfy the normalization agent contract

  @IT-36R4
  Rule: The normalization agent behaves as a bounded worker

    @IT-36R4S1
    Scenario: Return only contracted output or a contracted exception
      Given the normalization agent receives a governed source constraint
      When the normalization agent completes its work
      Then it returns normalized governed constraint RDF or a normalization exception
      And it does not modify downstream Logical Schema binding knowledge
      And it does not resolve context
      And it does not classify validation behavior
      And it does not generate Instance RDF bindings
      And it does not generate SHACL
      And it does not generate report findings
