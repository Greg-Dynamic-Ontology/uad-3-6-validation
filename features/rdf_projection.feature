  Feature: RDF projection of a loaded UAD appraisal

  As the UAD validation service
  I want to project a loaded UAD XML appraisal into RDF
  So that later validation stages can operate on a canonical graph representation

  Background:
    Given a schema-valid UAD XML appraisal is loaded

  Rule: RDF projection uses the loaded appraisal

    Scenario: Project the loaded UAD XML appraisal into RDF
      When the implemented RDF Projection stage runs
      Then the loaded UAD XML appraisal is projected into an RDF instance graph
      And the RDF instance graph faithfully represents the loaded UAD XML appraisal
      And the RDF Projection stage completes successfully

    Scenario: RDF projection does not require the appraisal to be selected again
      When the implemented RDF Projection stage runs
      Then the previously loaded UAD XML appraisal is used
      And the user is not asked to select the appraisal again

  Rule: RDF projection produces the RDF instance graph

    Scenario: Preserve the projected RDF instance graph
      When the implemented RDF Projection stage completes successfully
      Then the validation run contains the RDF instance graph
      And the RDF instance graph is available to the next configured pipeline stage

    Scenario: Preserve traceability to the source XML appraisal
      When the implemented RDF Projection stage completes successfully
      Then the RDF instance graph is associated with the loaded XML appraisal
      And the validation run records that RDF Projection produced the graph

  Rule: User experience controls technical visibility

    Scenario: User experience hides RDF implementation details
      Given the active configuration selects the User experience
      When the configured RDF Projection stage runs successfully
      Then the user sees validation progress
      And the user does not see RDF implementation details
      And the user is not offered technical RDF artifacts

    Scenario: Developer experience shows RDF projection status
      Given the active configuration selects the Developer experience
      When the configured RDF Projection stage runs successfully
      Then the developer sees that RDF Projection completed
      And the developer sees that an RDF instance graph was generated
      And technical RDF artifacts may be made available for inspection

  Rule: RDF projection failures are reported clearly

    Scenario: RDF projection cannot create an RDF instance graph
      Given the loaded UAD XML appraisal cannot be projected
      When the configured RDF Projection stage runs
      Then the RDF Projection stage fails
      And the validation run records the projection failure
      And later pipeline stages that require the RDF instance graph do not run
      And the application displays an understandable failure status

  Rule: Projection is deterministic

    Scenario: Reproject the same loaded appraisal
      Given the same schema-valid UAD XML appraisal is loaded
      When the configured RDF Projection stage runs more than once
      Then each run produces an equivalent RDF instance graph
      And the RDF Projection preserves the business meaning of the loaded appraisal