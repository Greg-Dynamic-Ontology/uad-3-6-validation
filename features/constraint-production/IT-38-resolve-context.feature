Feature: 3 Resolve governed constraint context
  As the governed constraint-production process
  I want a context-resolution agent to determine the applicable governed context for each bound constraint
  So that downstream agents apply the constraint only where the governed knowledge permits it

  Background:
    Given a normalized governed constraint is available
    And the normalized constraint is bound to a governed Logical Schema resource
    And the Logical Schema Model is available
    And the governed source context fields are available
    And the context-resolution agent has an explicit input, output, and error contract

  # IT-38R1 — Produce governed applicable context

  @IT-38R1
  Rule: Resolve one governed applicable context when the graph and source knowledge determine it

    @IT-38R1S1
    Scenario: Resolve one applicable context for a bound constraint
      Given a bound governed constraint identifies its Logical Schema resource
      And the governed source constraint identifies its source context
      And exactly one Logical Schema path is consistent with that source context
      When the context-resolution agent executes
      Then one governed applicable context is produced
      And the context preserves the normalized constraint identity
      And the context preserves the governed Logical Schema identities along the resolved path
      And the context preserves the governed source context knowledge
      And the context remains traceable to the governed source constraint
      And the context remains traceable to the Logical Schema Model
      And the resolved context is available to downstream constraint-production agents

  # IT-38R2 — Preserve ordered context knowledge

  @IT-38R2
  Rule: Preserve the governed order of schema resources that defines the applicable context

    @IT-38R2S1
    Scenario: Represent an applicable context as an ordered governed schema path
      Given a governed applicable context has been resolved
      When the context-resolution agent records that context
      Then the schema resources that define the context are recorded in order
      And each resource in the ordered path retains its governed Logical Schema identity
      And the constrained data point remains the terminal governed resource of the applicable path
      And downstream agents can distinguish this context from other contexts that use the same data point name

  # IT-38R3 — Reject unresolved or ambiguous context

  @IT-38R3
  Rule: Do not invent an applicable context when governed knowledge does not determine one

    @IT-38R3S1
    Scenario: Reject a bound constraint when no governed context can be resolved
      Given a bound governed constraint identifies its Logical Schema resource
      And no Logical Schema path is consistent with the governed source context
      When the context-resolution agent executes
      Then no applicable context is produced for that constraint
      And an exception is produced
      And the exception identifies the normalized constraint
      And the exception identifies the context-resolution stage
      And the exception identifies the unresolved source context knowledge
      And the agent does not invent a schema path or context
      And the exception is eligible to be written to the Batch Results Graph

    @IT-38R3S2
    Scenario: Reject a bound constraint when more than one incompatible context is permitted
      Given a bound governed constraint identifies its Logical Schema resource
      And more than one incompatible Logical Schema path is consistent with the governed source context
      When the context-resolution agent executes
      Then no candidate path is selected merely because it is statistically plausible
      And no applicable context is produced for that constraint
      And an exception is produced
      And the exception records the candidate governed contexts
      And the constraint is routed for review

  # IT-38R4 — Satisfy the context-resolution agent contract

  @IT-38R4
  Rule: The context-resolution agent behaves as a bounded worker

    @IT-38R4S1
    Scenario: Return only contracted output or a contracted exception
      Given the context-resolution agent receives a governed Logical Schema binding
      When the context-resolution agent completes its work
      Then it returns a governed applicable context or a context-resolution exception
      And it does not change normalized governed constraint meaning
      And it does not change the governed Logical Schema binding
      And it does not classify validation behavior
      And it does not generate Instance RDF bindings
      And it does not generate SHACL
      And it does not generate report findings
