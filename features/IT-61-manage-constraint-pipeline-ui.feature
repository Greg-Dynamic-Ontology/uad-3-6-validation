@IT-61
Feature: Manage constraint construction through the pipeline UI
  As a user responsible for governed constraints
  I want to select a governed workbook and process one row, a selected group of rows, or all rows through the
  constraint-construction pipeline so that I can inspect the RDF produced at every stage and review or replay
  a completed run.

  Background:
    Given the constraint-construction pipeline from IT-50 through IT-58 is available
    And each pipeline stage exchanges governed RDF knowledge
    And the configured source-workbook collection is available to the UI
    And each source workbook identifies its governed rule-data worksheet

  @IT-61R1
  Rule: A user selects the governed source and row scope for a construction run

    @IT-61R1S1
    Scenario: Select a configured GSE workbook for a construction run
      Given the configuration contains one or more governed source workbooks
      When the user selects a source workbook in the UI
      Then the UI identifies the selected workbook and its configured rule-data worksheet
      And the selection applies to that construction run
      And the UI does not change the governed source workbook

    @IT-61R1S2
    Scenario: Process one governed constraint row by its exact identifier
      Given the user has selected a governed source workbook
      And the workbook contains a row with a governed identifier
      When the user enters that identifier and starts a construction run
      Then the pipeline processes only the row with that exact identifier
      And the identifier is treated as text with leading zeroes preserved
      And the run records the selected workbook, worksheet, and row identifier

    @IT-61R1S3
    Scenario: Process a selected group of governed constraint rows
      Given the user has selected a governed source workbook
      And the workbook contains multiple governed constraint rows
      When the user selects a group of row identifiers and starts a construction run
      Then the pipeline processes each selected row exactly once
      And the pipeline does not process rows outside the selected group
      And each identifier is treated as text with leading zeroes preserved
      And each row result records its source workbook, worksheet, and identifier

    @IT-61R1S4
    Scenario: Process all governed constraint rows in the selected workbook
      Given the user has selected a governed source workbook
      When the user starts a construction run for all rows
      Then the pipeline processes each governed row from the selected worksheet
      And each row retains its own governed identifier and source provenance
      And the UI reports progress and completion for the full run

  @IT-61R2
  Rule: The UI runs construction stages in their governed order

    @IT-61R2S1
    Scenario: Execute the constraint-construction stages in order
      Given the user has started a construction run
      When the pipeline processes a selected constraint row
      Then the stages execute in this order:
        | order | stage                                      |
        | 1     | IT-50 Normalize governed constraints       |
        | 2     | IT-51 Exchange governed RDF                |
        | 3     | IT-52 Bind to the Logical Schema            |
        | 4     | IT-53 Resolve context                      |
        | 5     | IT-54 Classify validation behavior          |
        | 6     | IT-55 Bind instance RDF                    |
        | 7     | IT-56 Generate SHACL                       |
        | 8     | IT-57 Project report findings              |
        | 9     | IT-58 Execute the construction pipeline    |
      And each completed stage makes its output available to the next stage

    @IT-61R2S2
    Scenario: Show the RDF result produced by each completed stage
      Given a construction run has completed one or more stages
      When the user opens the run's stage timeline
      Then the UI lists each completed stage in execution order
      And each stage provides access to its produced RDF result
      And an incomplete stage is not shown as having produced a result

  @IT-61R3
  Rule: The UI visualizes each stage's serialized RDF knowledge

    @IT-61R3S1
    Scenario: Visualize a stage result as an RDF graph and Turtle
      Given a completed construction stage has produced serialized RDF
      When the user selects that stage in the UI
      Then the UI displays a graph visualization of that RDF
      And the UI provides the corresponding serialized Turtle
      And the graph visualization represents the triples in that serialization

    @IT-61R3S2
    Scenario: Step through RDF results from one stage to another
      Given a construction run has RDF results from multiple stages
      When the user moves to the next or previous stage
      Then the UI displays the selected stage's RDF result
      And the UI identifies the stage associated with the displayed result
      And moving between stages does not rerun the pipeline

    @IT-61R3S3
    Scenario: Play or pause a stage-by-stage RDF presentation
      Given a construction run has RDF results from multiple stages
      When the user starts stage playback
      Then the UI presents the stage results in execution order
      And the user can pause and resume playback
      And each displayed result remains associated with its stage

    @IT-61R3S4
    Scenario: Inspect the provenance of a displayed RDF result
      Given the user is viewing a stage's RDF result
      When the user opens its provenance details
      Then the UI identifies the governed source workbook and worksheet
      And the UI identifies the governed source row when the run is row-scoped
      And the UI identifies the stage activity that produced the result

  @IT-61R4
  Rule: A construction run can be saved and reviewed later

    @IT-61R4S1
    Scenario: Save the RDF results of a construction run
      Given a construction run has produced one or more stage results
      When the run results are saved
      Then the run retains the serialized RDF result for each completed stage
      And the run retains its source selection, row scope, and stage order
      And the saved results remain available for later review

    @IT-61R4S2
    Scenario: Replay a saved construction run
      Given a completed construction run and its stage results have been saved
      When the user opens the saved run and starts playback
      Then the UI presents the saved stage results in execution order
      And the UI does not execute the construction pipeline again
      And each result remains traceable to its saved run and stage activity

  @IT-61R5
  Rule: A failed stage is reported without inventing downstream RDF

    @IT-61R5S1
    Scenario: Stop a construction run when a stage fails
      Given a construction run is executing its stages
      When a stage returns a contracted failure or exception
      Then the UI identifies the failed stage and reports its diagnostic
      And the pipeline does not execute dependent downstream stages
      And the UI preserves access to results from stages that completed successfully
      And the UI does not display invented RDF for the failed or skipped stages
