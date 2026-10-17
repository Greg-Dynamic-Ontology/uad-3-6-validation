Feature: Build and inspect a governed constraint set
  As an authorized constraint-set operator
  I want to select a governed source and build its constraints through the construction pipeline
  So that I can inspect the RDF produced at each stage and revisit completed builds

  Background:
    Given the constraint-construction stages IT-50 through IT-58 are available
    And each stage exposes its governed RDF result and execution provenance
    And completed build runs can preserve their stage results as a run bundle

  @IT-59R1
  Rule: The operator selects one governed constraint set as the build input

    @IT-59R1S1
    Scenario: Select a constraint set by its governing authority
      Given governed constraint sets are registered with their source workbooks and versions
      When the operator selects a governing authority
      Then the workbench lists the applicable constraint sets for that authority
      And each listed set identifies its source workbook, worksheet, and governed version

    @IT-59R1S2
    Scenario: Select one registered constraint set for a build
      Given the workbench lists registered constraint sets
      When the operator selects one constraint set
      Then the selected set is clearly identified as the build input
      And no other constraint set is included in that build

    @IT-59R1S3
    Scenario: Prevent a build without a selected constraint set
      Given no constraint set is selected
      When the operator requests a build
      Then the workbench does not start a construction run
      And it identifies that a constraint set must be selected

  @IT-59R2
  Rule: A build processes the selected constraint set through the governed stages

    @IT-59R2S1
    Scenario: Build all rows in the selected constraint set
      Given the operator has selected one governed constraint set
      When the operator activates the Build action
      Then the workbench starts a construction run for every governed row in that set
      And each row is processed through IT-50 to IT-58
      And the run records the selected set and its source version

    @IT-59R2S2
    Scenario: Keep each build run distinct
      Given a completed build run exists for a constraint set
      When the operator builds that set again
      Then the workbench creates a distinct run
      And the previous run and its stage results remain unchanged

  @IT-59R3
  Rule: The workbench visualizes the actual RDF result of each construction stage

    @IT-59R3S1
    Scenario: Watch a running build advance through its construction stages
      Given a construction run is in progress
      When the operator views the build visualization
      Then the workbench shows the stages in pipeline order from IT-50 through IT-58
      And the visualization corresponds to the RDF results produced by that run
      And the workbench identifies the stage currently being processed

    @IT-59R3S2
    Scenario: Inspect a stage result while viewing the build
      Given a construction run has produced an RDF result for a stage
      When the operator selects that stage in the visualization
      Then the workbench displays the graph represented by that stage result
      And the operator can inspect the exact serialized RDF for that result
      And the displayed RDF belongs to the selected run and stage

    @IT-59R3S3
    Scenario: Navigate the build visualization
      Given a construction run has stage results available
      When the operator uses the visualization controls
      Then the operator can pause and resume playback
      And the operator can move to the previous or next available stage
      And the operator can select a stage directly

  @IT-59R4
  Rule: A saved build run can be replayed from its preserved stage results

    @IT-59R4S1
    Scenario: Preserve the RDF results of every completed stage
      Given a construction run has completed
      When the run is saved
      Then the run bundle contains the serialized RDF result from each completed stage
      And the run bundle identifies the selected constraint set and source workbook
      And the run bundle records the stage order and execution provenance
      And the run bundle records an integrity digest for each serialized RDF result

    @IT-59R4S2
    Scenario: Replay a saved run without rerunning construction
      Given a saved construction run contains serialized stage results
      When the operator opens that run for review
      Then the workbench replays the preserved stage results in pipeline order
      And the workbench does not regenerate or alter those results

    @IT-59R4S3
    Scenario: Verify a saved stage result when it is opened
      Given a saved construction run contains an integrity digest for a stage result
      When the operator opens that stage result
      Then the workbench verifies the serialized RDF against its recorded digest
      And the workbench reports whether the result matches the saved run record

  @IT-59R5
  Rule: Build failures remain visible and traceable to their stage and source

    @IT-59R5S1
    Scenario: Show a construction-stage failure in the build visualization
      Given a construction run encounters a failure in a stage
      When the workbench displays the run
      Then it identifies the failed stage and affected source row when available
      And it displays the stage's contracted failure information
      And it does not present the run as a successful completed build

    @IT-59R5S2
    Scenario: Preserve completed stage results when a later stage fails
      Given a construction run has completed one or more stages
      And a later stage fails
      When the run is saved
      Then the run bundle preserves the results of the completed stages
      And the failure remains linked to the run, stage, and governed source row
      And no downstream result is invented for the failed stage