# IT-34-define-and-persist-constraint-construction-run-knowledge.feature

Feature: Define and persist governed constraint-construction run knowledge
  As the governed constraint-production process
  I want each constraint-construction execution represented as governed RDF graph knowledge
  So that agent activity, produced knowledge, timing, status, provenance, and execution order remain explicit and recoverable

  Background:
    Given constraint construction is a distinct operational mode from received-file validation
    And a constraint-construction execution may use multiple bounded agents
    And multiple construction activities may execute concurrently
    And execution order and disk-write order may differ
    And construction-run knowledge is persisted as RDF
    And PROV-O is reused for standard provenance relationships where applicable

  # IT-34R1 — Represent one construction execution as governed graph knowledge

  @IT-34R1
  Rule: Represent a constraint-construction execution with explicit run, activity, and result identities

    @IT-34R1S1
    Scenario: Represent one construction run with explicit run, activity, and result identities
      Given a constraint-production batch is selected for construction
      When a constraint-construction run is created
      Then the construction run has its own governed identity
      And each construction activity has its own identity
      And each construction result has its own identity
      And each construction activity identifies the governed constraint it is processing
      And each construction activity identifies the construction stage it performs
      And each construction activity identifies the agent that performed it
      And each construction activity identifies the governed knowledge it used
      And each construction result identifies the activity that generated it
      And each construction result identifies the governed constraint it concerns
      And each construction result records its construction-stage status
      And the run, activity, and result identities do not depend on disk-write order

  # IT-34R2 — Preserve temporal and causal order independently of write order

  @IT-34R2
  Rule: Construction-run knowledge must preserve temporal and causal relationships during concurrent execution

    @IT-34R2S1
    Scenario: Record activity timing independently of graph write order
      Given more than one construction activity may execute concurrently
      When construction activities start and complete
      Then each activity records its own start time
      And each completed activity records its own end time
      And each generated result remains linked to the activity that generated it
      And activity timing can be used to order execution independently of the order in which triples were written
      And concurrent activities do not require a parent-child tree relationship

    @IT-34R2S2
    Scenario: Preserve graph relationships among shared construction knowledge
      Given one construction result may be used by more than one later construction activity
      When those activities consume the result
      Then each consuming activity identifies the same governed result as used knowledge
      And the result is not duplicated merely to preserve a tree structure
      And the execution topology remains representable as a directed graph

  # IT-34R3 — Keep construction-run knowledge separate from validation-run knowledge

  @IT-34R3
  Rule: Constraint-construction execution knowledge must not be confused with received-file validation execution knowledge

    @IT-34R3S1
    Scenario: Represent only constraint-construction activity in a construction run
      Given a constraint-construction run is active
      When construction-run knowledge is recorded
      Then the run records activities that construct governed constraint knowledge
      And the run may record normalization, Logical Schema binding, context resolution, validation behavior, Instance RDF binding, SHACL generation, and finding-definition activity
      And the run does not represent validation of a received appraisal file
      And the run does not represent production SHACL ValidationResults from a received file
      And the run does not represent production governed findings from a received file

  # IT-34R4 — Persist one RDF graph per construction execution

  @IT-34R4
  Rule: Each constraint-construction execution has its own persistent RDF results graph

    @IT-34R4S1
    Scenario: Keep an active construction-run graph current on disk
      Given a constraint-construction run has been created
      And the run has its own persistent RDF results graph
      When construction knowledge for the run is added or changed
      Then the current run graph is updated
      And the updated run graph is written to disk before processing continues
      And the disk copy reflects the latest completed construction event
      And run-specific knowledge remains distinguishable from knowledge produced by other runs

    @IT-34R4S2
    Scenario: Freeze a completed construction-run graph
      Given a constraint-construction run has completed
      When the final construction-run state is persisted
      Then the completed run graph is retained as the governed record of that execution
      And a later retry or new execution uses a new construction-run identity
      And a later execution does not overwrite the completed run graph
      And completed run graphs can be compared without reconstructing prior execution state

  # IT-34R5 — Use standard provenance relationships where they already express the required knowledge

  @IT-34R5
  Rule: Reuse PROV-O for common execution and provenance semantics

    @IT-34R5S1
    Scenario: Represent common provenance using PROV-O
      Given a construction activity uses governed knowledge
      And the activity generates new governed knowledge
      And the activity is performed by an agent
      When the construction-run RDF is written
      Then used knowledge is related to the activity with PROV-O semantics
      And generated knowledge is related to the generating activity with PROV-O semantics
      And the activity is related to the performing agent with PROV-O semantics
      And activity start and end times use PROV-O temporal semantics
      And UAD-specific predicates are introduced only for construction-domain knowledge not already expressed adequately by PROV-O
