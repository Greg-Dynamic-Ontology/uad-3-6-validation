# This feature file describes the requirements for governing and validating UAD application configuration knowledge.
# The configuration is represented as RDF, and the validation process ensures that the configuration adheres to a
# defined vocabulary and meets specific governance rules.
#
# It was discovered after Iteration 61 that the configuration knowledge was not being validated against a governed
# vocabulary, which could lead to inconsistencies and errors in the application behavior.
# This feature addresses that gap by introducing validation checks for configuration RDF.
#
# It should be managed and run prior to IT-1.
@IT-62
Feature: Govern and validate UAD application configuration knowledge
  As the UAD validation process
  I want configuration RDF to use a defined, validated vocabulary
  So that configuration changes remain explicit, testable, and consistent with the application

  Background:
    Given the UAD application configuration is represented as RDF
    And the configuration vocabulary is available as RDF
    And configuration validation checks the configuration graph against that vocabulary and its governed requirements

  @IT-62R1
  Rule: Every configuration vocabulary term used by configuration RDF is defined

    @IT-62R1S1
    Scenario: Detect configuration terms that have no vocabulary definition
      Given a configuration graph uses a configuration class or property
      And that term has no definition in the configuration vocabulary
      When the configuration knowledge is validated
      Then validation rejects the configuration graph
      And the diagnostic identifies every undefined configuration term

    @IT-62R1S2
    Scenario: Accept configuration RDF whose classes and properties are defined
      Given the configuration graph uses configuration classes and properties
      And every used class and property is defined by the configuration vocabulary
      When the configuration knowledge is validated
      Then the configuration graph passes vocabulary validation

  @IT-62R2
  Rule: The active compliance source is selected from the configured source-workbook collection

    @IT-62R2S1
    Scenario: Accept one active workbook that belongs to the available source collection
      Given the configuration lists the available governed GSE workbooks
      And exactly one listed workbook is selected as the active compliance source
      When the configuration knowledge is validated
      Then the active compliance source is accepted

    @IT-62R2S2
    Scenario Outline: Reject an invalid active-workbook selection
      Given the configured source-workbook collection contains the available workbooks
      And the active compliance source is <selection>
      When the configuration knowledge is validated
      Then validation rejects the active-workbook selection
      And the diagnostic explains that <reason>

      Examples:
        | selection                         | reason                                      |
        | absent                            | exactly one active source is required      |
        | a workbook outside the collection | the active source must be listed            |
        | multiple workbooks                | exactly one active source is required      |

  @IT-62R3
  Rule: Each governed source workbook identifies its location and rule-data worksheet

    @IT-62R3S1
    Scenario: Accept a workbook with one configured path and rule-data worksheet
      Given a governed source workbook is configured
      And it has a source file location
      And it has one rule-data worksheet name
      When the configuration knowledge is validated
      Then the workbook source definition is accepted

    @IT-62R3S2
    Scenario Outline: Reject an incomplete or ambiguous workbook source definition
      Given a governed source workbook is configured with <worksheet_definition>
      When the configuration knowledge is validated
      Then validation rejects the workbook source definition
      And the diagnostic identifies <reason>

      Examples:
        | worksheet_definition       | reason                                      |
        | no rule-data worksheet     | the required worksheet name is missing     |
        | multiple rule-data sheets  | exactly one rule-data worksheet is required|
        | no source file location    | the required workbook location is missing  |

  @IT-62R4
  Rule: Configuration vocabulary and configuration data remain synchronized

    @IT-62R4S1
    Scenario: Identify vocabulary drift when configuration terms change
      Given a configuration graph uses a configuration term
      When the configuration vocabulary synchronization check runs
      Then every used configuration class and property has a vocabulary definition
      And newly used terms are reported when they have not yet been defined