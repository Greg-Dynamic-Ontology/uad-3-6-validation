Feature: 5 Bind governed validation behavior to Instance RDF
  As the governed constraint-production process
  I want an Instance RDF binding agent to bind context-resolved validation behavior to the established Instance RDF representation
  So that executable validation can operate on the RDF actually produced from UAD instance data

  Background:
    Given a normalized governed constraint is available
    And the normalized constraint is bound to a governed Logical Schema resource
    And the governed applicable context has been resolved
    And the governed validation behavior has been classified
    And the Instance RDF projection model is available
    And the Instance RDF binding agent has an explicit input, output, and error contract

  # IT-40R1 — Produce an Instance RDF binding

  @IT-40R1
  Rule: Bind governed validation knowledge to the established Instance RDF representation

    @IT-40R1S1
    Scenario: Bind a governed constraint to one Instance RDF representation
      Given the governed applicable context identifies the Logical Schema resources required by the constraint
      And the Instance RDF projection model defines how those resources are represented in Instance RDF
      And exactly one Instance RDF binding is consistent with the governed context and projection model
      When the Instance RDF binding agent executes
      Then one governed Instance RDF binding is produced
      And the binding preserves the normalized constraint identity
      And the binding preserves the governed Logical Schema binding
      And the binding preserves the governed applicable context
      And the binding preserves the governed validation behavior
      And the binding uses the established Instance RDF representation
      And the binding remains traceable to the governed source constraint
      And the binding is available to downstream constraint-production agents

  # IT-40R2 — Conform to the established Instance RDF projection model

  @IT-40R2
  Rule: Instance RDF binding must describe the existing projection rather than redesign it

    @IT-40R2S1
    Scenario: Reuse the RDF terms produced by the Instance RDF projector
      Given the Instance RDF projector has an established representation for the required instance data
      When the Instance RDF binding agent records the binding
      Then the binding uses the RDF classes and predicates produced by the established projector
      And existing projector identities are preserved exactly
      And the agent does not replace established RDF terms with preferred alternative terms
      And the agent does not require the Instance RDF projector to change in order to simplify validation
      And the binding describes how governed validation knowledge reaches the projected instance data

  # IT-40R3 — Reject unresolved or ambiguous Instance RDF bindings

  @IT-40R3
  Rule: Do not invent an Instance RDF binding when the established projection does not determine one

    @IT-40R3S1
    Scenario: Reject a constraint when no Instance RDF binding can be resolved
      Given the governed applicable context has been resolved
      And the required Logical Schema resource has no established representation in the Instance RDF projection model
      When the Instance RDF binding agent executes
      Then no Instance RDF binding is produced for that constraint
      And an exception is produced
      And the exception identifies the normalized constraint
      And the exception identifies the Instance RDF binding stage
      And the exception identifies the unresolved governed schema or context knowledge
      And the agent does not invent an RDF class, predicate, or path
      And the exception is eligible to be written to the Batch Results Graph

    @IT-40R3S2
    Scenario: Reject a constraint when more than one incompatible Instance RDF binding is possible
      Given the governed applicable context has been resolved
      And more than one incompatible Instance RDF binding is consistent with the established projection model
      When the Instance RDF binding agent executes
      Then no candidate binding is selected merely because it is statistically plausible
      And no Instance RDF binding is produced for that constraint
      And an exception is produced
      And the exception records the candidate Instance RDF bindings
      And the constraint is routed for review

  # IT-40R4 — Satisfy the Instance RDF binding agent contract

  @IT-40R4
  Rule: The Instance RDF binding agent behaves as a bounded worker

    @IT-40R4S1
    Scenario: Return only contracted output or a contracted exception
      Given the Instance RDF binding agent receives a context-resolved constraint with governed validation behavior
      When the Instance RDF binding agent completes its work
      Then it returns a governed Instance RDF binding or an Instance RDF binding exception
      And it does not change normalized governed constraint meaning
      And it does not change the governed Logical Schema binding
      And it does not change the governed applicable context
      And it does not change the governed validation behavior
      And it does not generate SHACL
      And it does not generate report findings
