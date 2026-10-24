@IT-58
Feature: Execute the governed constraint-production pipeline
  As a user of the constraint-production process
  I want to process one governed row or all governed rows from a configured CSV, Excel, or other supported governed source
  So that each selected constraint becomes a reusable, traceable RDF and SHACL artifact

  Background:
    Given the configuration identifies the active governed constraint source
    And the configuration identifies its source format and file location
    And an Excel source identifies its configured worksheet
    And the governed source reader supplies the same row contract for each supported format
    And governed source row identifiers are preserved as text
    And the constraint-production workers for IT-50 through IT-56 are available
    And each worker has an explicit input, output, and error contract
    And the Batch Results Graph is available for persistent production state
    And each handoff follows the governed RDF exchange contract defined by IT-51
    And a worker may consume only verified output from its preceding production stage

  # IT-58R1 — Select one row or all rows for production

  @IT-58R1
  Rule: The pipeline processes exactly the governed source rows requested

    @IT-58R1S1
    Scenario: Process one governed source row into reusable constraint artifacts
      Given the user requests "Process row with ID=x" for a governed source row ID
      And that row contains sufficient governed knowledge for constraint production
      When the constraint-production pipeline processes the request
      Then only the requested source row is selected for production
      And its data advances through normalization, Logical Schema binding, context resolution, validation-behavior classification, Instance RDF binding, and SHACL generation
      And every production stage consumes only verified output from its preceding stage
      And the completed RDF and SHACL artifacts remain traceable to the selected governed source row
      And no appraisal XML report is required to produce or complete the constraint artifacts
      And other source rows are not processed by this request

    @IT-58R1S2
    Scenario: Process all governed source rows into reusable constraint artifacts
      Given the user requests "Process all rows"
      When the constraint-production pipeline processes the request
      Then every governed source row is considered for production
      And each row is processed independently through normalization, Logical Schema binding, context resolution, validation-behavior classification, Instance RDF binding, and SHACL generation
      And every production stage consumes only verified output from its preceding stage
      And each successfully processed row has reusable RDF and SHACL artifacts traceable to that governed source row
      And each row that cannot complete production has its exception recorded
      And a row-level exception does not prevent other eligible rows from being processed
      And no appraisal XML report is required to produce the constraint artifacts

  # IT-58R2 — Enforce verified handoffs between production stages

  @IT-58R2
  Rule: A production stage may consume only verified output from its preceding stage

    @IT-58R2S1
    Scenario: Prevent downstream production before upstream output is verified
      Given a governed source row is being processed
      And an upstream production stage has produced output that is not verified GREEN
      When the pipeline considers the next production stage for that row
      Then the downstream production stage does not execute for that row
      And the row remains at the current production stage
      And the Batch Results Graph records the current stage state
      And unverified output is not treated as governed input to a downstream stage

  # IT-58R3 — Record exceptions independently for each row

  @IT-58R3
  Rule: A contracted worker exception stops downstream production for its row while allowing other rows to proceed

    @IT-58R3S1
    Scenario: Record a production exception for one row and continue eligible rows
      Given multiple governed source rows are selected for production
      And a production worker cannot satisfy its contract for one selected row
      When that worker returns a contracted exception for the row
      Then no downstream production stage executes for that row
      And the row is marked as an exception
      And the failed production stage and exception reason are recorded in the Batch Results Graph
      And the last verified production stage remains recorded for that row
      And the row is eligible for governed review
      And other eligible rows may continue through the production pipeline

  # IT-58R4 — Resume a row from governed persistent state

  @IT-58R4
  Rule: Resume a resolved row without repeating its verified production stages

    @IT-58R4S1
    Scenario: Resume production after a recorded row exception is resolved
      Given a governed source row has a recorded exception in the Batch Results Graph
      And the exception has been resolved through governed review
      And all production stages before the exception remain verified GREEN
      When the constraint-production pipeline resumes that row
      Then processing resumes at the stage that previously reported the exception
      And previously verified production stages are not repeated
      And downstream stages execute only after the resumed stage is verified GREEN
      And the Batch Results Graph is updated as production proceeds

  # IT-58R5 — Keep orchestration separate from worker responsibilities and report evaluation

  @IT-58R5
  Rule: The pipeline coordinates production without taking over worker or appraisal-report evaluation responsibilities

    @IT-58R5S1
    Scenario: Keep constraint knowledge transformations inside their contracted workers
      Given the constraint-production pipeline is processing a governed source row
      When that row advances through production
      Then normalized constraint knowledge is produced only by the IT-50 normalization worker
      And Logical Schema binding knowledge is produced only by the IT-52 binding worker
      And applicable context knowledge is produced only by the IT-53 context worker
      And validation behavior knowledge is produced only by the IT-54 classification worker
      And Instance RDF binding knowledge is produced only by the IT-55 binding worker
      And executable SHACL is produced only by the IT-56 generation worker
      And the IT-51 RDF exchange contract governs the handoffs between workers
      And the pipeline coordinates row selection, handoffs, verification, exceptions, and persistence
      And appraisal XML evaluation and runtime finding projection are not performed by this production pipeline

    @IT-58R5S2
    Scenario: Keep appraisal-report evaluation separate from constraint production
      Given a governed source row has completed constraint production
      When the pipeline records the row's production result
      Then the reusable constraint RDF and SHACL artifacts are available for later appraisal-report evaluation
      And the pipeline does not require an appraisal XML report
      And the pipeline does not execute SHACL against an appraisal report
      And runtime findings are produced by the report-evaluation process defined by IT-57

  # IT-58R6 — Complete production only from verified reusable artifacts

  @IT-58R6
  Rule: A row is complete only when all required reusable constraint artifacts are verified

    @IT-58R6S1
    Scenario: Mark a source row complete after successful constraint production
      Given a governed source row has passed through all required production stages from IT-50 through IT-56
      And every required production stage is verified GREEN
      And the completed RDF and SHACL artifacts are available
      And no unresolved production exception remains for the row
      When the pipeline evaluates the row's production state
      Then the row is marked complete
      And the Batch Results Graph records the completed production state
      And the persistent graph identifies the verified production stages
      And the artifacts remain traceable to the governed source row
      And completion does not depend on appraisal XML evaluation or runtime findings