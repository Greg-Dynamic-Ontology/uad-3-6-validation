@IT-50 @constraint-production
Feature: Normalize governed constraints
  As the governed constraint-production process
  I want a normalization agent to transform governed rows from data-constraints.csv into normalized constraint knowledge
  So that downstream agents receive a stable, traceable, implementation-independent constraint representation

  Background:
    Given the normalization agent has an explicit input, output, and error contract

  @IT-50R1
  Rule: Produce normalized constraint RDF from sufficient governed source knowledge

    @IT-50R1S1
    Scenario: Produce normalized RDF from a governed source constraint
      Given a governed source row contains the Unique ID
      And the governed source row contains the data point name
      And the governed source row contains the source rule identifier
      And the governed source row contains the requirement text
      And the governed source row contains the violation condition
      And the governed source row contains the severity
      And the governed source row contains the source context fields
      And the governed source location is known
      And source provenance is available
      When the normalization agent executes
      Then a normalized governed constraint resource is produced
      And the normalized constraint preserves the governed Unique ID
      And the normalized constraint preserves the source rule identifier
      And the normalized constraint preserves the requirement text
      And the normalized constraint preserves the violation condition
      And the normalized constraint preserves the severity
      And the normalized constraint preserves the source context knowledge
      And the normalized constraint remains traceable to the governed source location
      And the normalized constraint remains traceable to its source provenance
      And the normalized constraint does not depend on a SHACL representation
      And the normalized constraint RDF is written to its governed project location

  @IT-50R2
  Rule: Normalization must not replace governed source knowledge with implementation-specific knowledge

    @IT-50R2S1
    Scenario: Preserve governed meaning independently of implementation technology
      Given a governed source constraint can be normalized
      When the normalization agent produces the normalized constraint RDF
      Then governed source identity remains authoritative
      And governed source meaning remains authoritative
      And implementation-specific identifiers do not replace governed identifiers
      And implementation-specific structures do not become the source of governed meaning
      And no SHACL-specific knowledge is required to state the normalized constraint

  @IT-50R3
  Rule: Do not invent normalized constraint knowledge when governed input is insufficient

    @IT-50R3S1
    Scenario: Reject a governed source row with insufficient required knowledge
      Given a governed source row is missing knowledge required by the normalization contract
      When the normalization agent executes
      Then no normalized governed constraint is produced for that row
      And an exception is produced
      And the exception identifies the governed source constraint when its identity is available
      And the exception identifies the normalization stage
      And the exception identifies the missing governed knowledge
      And the agent does not infer or invent a replacement value
      And the exception is eligible to be written to the Batch Results Graph

    @IT-50R3S2
    Scenario: Reject ambiguous governed source knowledge
      Given a governed source row contains more than one incompatible interpretation required for normalization
      When the normalization agent executes
      Then no interpretation is selected merely because it is statistically plausible
      And no normalized governed constraint is produced for that row
      And an exception is produced
      And the exception records the ambiguous governed knowledge
      And the constraint is routed for review

  @IT-50R4
  Rule: The normalization agent behaves as a bounded worker

    @IT-50R4S1
    Scenario: Return only contracted output or a contracted exception
      Given the normalization agent receives a governed source constraint
      When the normalization agent completes its work
      Then it returns normalized governed constraint RDF or a normalization exception
      And it does not modify downstream Logical Schema binding knowledge
      And it does not resolve context
      And it does not classify validation behavior
      And it does not generate Instance RDF bindings
      And it does not generate SHACL
      And it does not generate report findings

  @IT-50R5
  Rule: Read and normalize constraints directly from the authoritative CSV source

    @IT-50R5S1
    Scenario: Read a governed constraint row from data-constraints.csv
      Given data-constraints.csv is the authoritative governed source
      And a governed batch identifies one row by its Unique ID
      When the normalization process reads the selected row directly from the CSV
      Then the materialized source knowledge is derived from that CSV row
      And its governed Unique ID is preserved
      And its source row location is preserved
      And no XLS or XLSX conversion is required

    @IT-50R5S2
    Scenario: Produce normalized RDF from an actual governed CSV row
      Given a governed source row has been read from data-constraints.csv
      When the normalization agent processes that governed source knowledge
      Then normalized constraint RDF is produced
      And the normalized constraint remains traceable to the CSV row

    @IT-50R5S3
    Scenario: Reject a CSV whose headers do not match the governed structure
      Given data-constraints.csv does not contain the required governed source columns
      When the normalization process reads a selected row
      Then the CSV structure is rejected
      And no normalized governed constraint is produced
      And the rejection identifies the header mismatch

    @IT-50R5S4
    Scenario Outline: Reject a CSV selection that does not identify exactly one source row
      Given the requested governed Unique ID matches <matching_rows> rows in data-constraints.csv
      When the normalization process selects the source row
      Then the selection is rejected
      And no normalized governed constraint is produced
      And the rejection identifies "<reason>"

      Examples:
        | matching_rows | reason                              |
        | 0             | no matching governed source row    |
        | 2             | multiple matching governed rows   |

    @IT-50R5S5
    Scenario: Reject a CSV row with blank required governed knowledge
      Given a selected governed CSV row has a blank required field
      When the normalization agent processes the row
      Then no normalized governed constraint is produced
      And insufficient governed source knowledge is reported
      And the rejection identifies the missing CSV column

  @IT-50R6
  Rule: Record normalization test results as governed construction knowledge

    @IT-50R6S1
    Scenario: Record a GREEN normalization test result
      Given a normalization scenario is executed
      And the scenario passes
      When the test result is recorded
      Then a governed test-result resource is produced
      And the result identifies the scenario
      And the result records GREEN status
      And the result identifies the tested constraint when applicable
      And the result remains traceable to the test execution activity
      And the result remains traceable to the governed source artifacts used

    @IT-50R6S2
    Scenario: Record a RED normalization test result
      Given a normalization scenario is executed
      And the scenario fails
      When the test result is recorded
      Then a governed test-result resource is produced
      And the result identifies the scenario
      And the result records RED status
      And the failure reason is preserved
      And the result remains traceable to the test execution activity

    @IT-50R6S3
    Scenario: Preserve warnings without converting them into failure
      Given a normalization scenario passes
      And the test execution produces warnings
      When the test result is recorded
      Then the result records GREEN status
      And the warnings are preserved as test-execution knowledge
      And the warnings do not become constraint-production failures