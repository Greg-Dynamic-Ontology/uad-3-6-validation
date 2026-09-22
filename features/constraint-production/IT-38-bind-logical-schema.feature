Feature: 2 Bind governed constraints to the Logical Schema
  As the governed constraint-production process
  I want a Logical Schema binding agent to bind normalized constraint knowledge to governed Logical Schema resources
  So that downstream agents operate on stable schema identities rather than guessed element names or implementation-specific paths

  Background:
    Given a normalized governed constraint is available
    And the normalized constraint preserves its governed source identity and provenance
    And the Logical Schema Model is available
    And named Logical Schema resources preserve their governed source identities
    And the Logical Schema binding agent has an explicit input, output, and error contract

  # IT-38R1 — Produce governed Logical Schema bindings

  @IT-38R1
  Rule: Bind normalized constraint knowledge to governed Logical Schema resources

    @IT-38R1S1
    Scenario: Bind a normalized constraint to one matching Logical Schema resource
      Given a normalized governed constraint identifies a governed data point
      And exactly one governed Logical Schema resource matches that data point
      When the Logical Schema binding agent executes
      Then the normalized constraint is bound to that governed Logical Schema resource
      And the binding preserves the normalized constraint identity
      And the binding preserves the governed Logical Schema identity
      And the binding remains traceable to the governed source constraint
      And the binding remains traceable to the Logical Schema Model
      And the resulting binding is available to downstream constraint-production agents

  # IT-38R2 — Reuse governed Logical Schema identity

  @IT-38R2
  Rule: Reuse the governed Logical Schema identity rather than minting a replacement identity

    @IT-38R2S1
    Scenario: Preserve a named Logical Schema resource identity during binding
      Given a named Logical Schema resource has a governed source identity
      And a normalized constraint refers to that resource
      When the Logical Schema binding agent produces the binding
      Then the governed Logical Schema identity is reused
      And a generated replacement identity is not minted
      And the same governed Logical Schema resource can be reused by other constraints
      And implementation-specific identifiers do not become the governed schema identity

  # IT-38R3 — Reject unresolved or ambiguous bindings

  @IT-38R3
  Rule: Do not invent a Logical Schema binding when the graph does not determine one

    @IT-38R3S1
    Scenario: Reject a constraint when no Logical Schema resource can be resolved
      Given a normalized governed constraint identifies a governed data point
      And no governed Logical Schema resource matches that data point
      When the Logical Schema binding agent executes
      Then no Logical Schema binding is produced for that constraint
      And an exception is produced
      And the exception identifies the normalized constraint
      And the exception identifies the Logical Schema binding stage
      And the exception identifies the unresolved governed data point
      And the agent does not invent a schema resource or schema identity
      And the exception is eligible to be written to the Batch Results Graph

    @IT-38R3S2
    Scenario: Reject a constraint when more than one incompatible Logical Schema binding is possible
      Given a normalized governed constraint identifies a governed data point
      And more than one incompatible governed Logical Schema resource matches that data point
      When the Logical Schema binding agent executes
      Then no matching resource is selected merely because it is statistically plausible
      And no Logical Schema binding is produced for that constraint
      And an exception is produced
      And the exception records the candidate governed Logical Schema resources
      And the constraint is routed for review

  # IT-38R4 — Satisfy the Logical Schema binding agent contract

  @IT-38R4
  Rule: The Logical Schema binding agent behaves as a bounded worker

    @IT-38R4S1
    Scenario: Return only contracted output or a contracted exception
      Given the Logical Schema binding agent receives a normalized governed constraint
      When the Logical Schema binding agent completes its work
      Then it returns a governed Logical Schema binding or a Logical Schema binding exception
      And it does not change normalized governed constraint meaning
      And it does not resolve applicable context
      And it does not classify validation behavior
      And it does not generate Instance RDF bindings
      And it does not generate SHACL
      And it does not generate report findings
