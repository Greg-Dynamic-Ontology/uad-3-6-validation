Feature: Execute the governed constraint-production pipeline
  As the governed constraint-production process
  I want the seven constraint-production agents to execute as one governed pipeline
  So that a source constraint advances only through verified knowledge transformations and stops when any agent cannot satisfy its contract

  Background:
    Given a governed source constraint is eligible for constraint production
    And the seven constraint-production agents are available
    And each agent has an explicit input, output, and error contract
    And the Batch Results Graph is available for persistent production state
    And a constraint may advance only from verified output of one agent to the next agent

  # IT-43R1 — Execute the seven agents in governed order

  @IT-43R1
  Rule: Advance a governed constraint through the constraint-production agents in order

    @IT-43R1S1
    Scenario: Advance one governed constraint through all seven agents
      Given the governed source constraint contains sufficient knowledge for normalization
      And each downstream agent can satisfy its contract for the constraint
      When the governed constraint-production pipeline executes
      Then the normalization agent executes first
      And the Logical Schema binding agent receives the verified normalized constraint RDF
      And the context-resolution agent receives the verified Logical Schema binding
      And the validation-behavior agent receives the verified applicable context
      And the Instance RDF binding agent receives the verified validation behavior
      And the SHACL-generation agent receives the verified Instance RDF binding
      And SHACL validation executes using the verified SHACL representation
      And the report-finding agent receives the SHACL validation report and governed constraint knowledge
      And each completed production stage is recorded in the Batch Results Graph
      And the constraint is complete only after every required production stage succeeds

  # IT-43R2 — Enforce verified handoffs between agents

  @IT-43R2
  Rule: An agent may consume only verified output from its immediate upstream production stage

    @IT-43R2S1
    Scenario: Prevent downstream execution before upstream output is verified
      Given a governed constraint is being processed
      And an upstream agent has produced output that has not been verified GREEN
      When the pipeline considers the next production stage
      Then the downstream agent does not execute for that constraint
      And the constraint remains at the current production stage
      And the Batch Results Graph records the current stage state
      And unverified knowledge is not treated as governed input to a downstream agent

  # IT-43R3 — Stop one constraint when an agent reports an exception

  @IT-43R3
  Rule: A contracted agent exception stops downstream production for that constraint without stopping eligible constraints

    @IT-43R3S1
    Scenario: Stop advancement when an agent reports an exception
      Given a governed constraint is being processed
      And one constraint-production agent cannot satisfy its contract
      When that agent returns a contracted exception
      Then no downstream agent executes for that constraint
      And the constraint is marked as an exception
      And the failed production stage is recorded in the Batch Results Graph
      And the exception reason is recorded in the Batch Results Graph
      And the last verified production stage remains recorded
      And the constraint is eligible for governed review
      And other eligible constraints may continue through the production pipeline

  # IT-43R4 — Resume a constraint from governed persistent state

  @IT-43R4
  Rule: Resume resolved constraints without repeating already verified production stages

    @IT-43R4S1
    Scenario: Resume production after a recorded exception is resolved
      Given a governed constraint has a recorded exception in the Batch Results Graph
      And the exception has been resolved through governed review
      And all production stages before the exception remain verified GREEN
      When the constraint-production pipeline resumes that constraint
      Then processing resumes at the stage that previously reported the exception
      And previously verified production stages are not repeated
      And downstream agents execute only after the resumed stage is verified GREEN
      And the Batch Results Graph is updated as production proceeds

  # IT-43R5 — Preserve the seven agent boundaries during orchestration

  @IT-43R5
  Rule: Pipeline orchestration coordinates agents without absorbing their knowledge-transformation responsibilities

    @IT-43R5S1
    Scenario: Keep production responsibilities inside their contracted agents
      Given the governed constraint-production pipeline is executing
      When a constraint advances through production
      Then normalization knowledge is produced only by the normalization agent
      And Logical Schema binding knowledge is produced only by the Logical Schema binding agent
      And applicable context knowledge is produced only by the context-resolution agent
      And validation behavior knowledge is produced only by the validation-behavior agent
      And Instance RDF binding knowledge is produced only by the Instance RDF binding agent
      And executable SHACL is produced only by the SHACL-generation agent
      And governed report findings are produced only by the report-finding agent
      And the pipeline itself coordinates handoffs, verification state, exceptions, and persistence

  # IT-43R6 — Complete production only from governed successful state

  @IT-43R6
  Rule: Do not declare a constraint complete unless every required production stage is verified

    @IT-43R6S1
    Scenario: Mark a constraint complete after the full governed production chain succeeds
      Given a governed constraint has passed through all seven constraint-production agents
      And every required production stage is verified GREEN
      And no unresolved exception remains for the constraint
      When the pipeline evaluates the constraint production state
      Then the constraint is marked complete
      And the Batch Results Graph records the completed production state
      And the persistent graph identifies the verified production stages
      And the completed constraint remains traceable to its governed source knowledge
