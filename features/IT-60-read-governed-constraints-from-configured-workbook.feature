@IT-60
Feature: Read governed constraints from a configured GSE workbook
  As the UAD validation process
  I want to read governed constraint rows directly from the active GSE workbook and configured worksheet
  So that production evaluators use authoritative source values without CSV import interpretation

  Background:
    Given the UAD configuration identifies the active compliance source workbook
    And the active workbook configuration identifies a worksheet name
    And the active workbook is a published GSE compliance workbook

  @IT-60R1
  Rule: Read constraint rows from the configured active workbook and worksheet

    @IT-60R1S1
    Scenario: Read governed rows from the configured workbook tab
      Given the configured workbook exists
      And it contains the configured worksheet
      When the runtime loads governed constraint rows
      Then it reads the rows from that workbook and worksheet
      And each row retains its governed source fields
      And loading the rows does not require an intermediate CSV file

    @IT-60R1S2
    Scenario: Reject a configured worksheet that does not exist
      Given the configured workbook exists
      And it does not contain the configured worksheet
      When the runtime loads governed constraint rows
      Then it returns a contracted source-configuration error
      And it does not silently select a different worksheet

    @IT-60R1S3
    Scenario: Read from the workbook selected by active source configuration
      Given the configuration contains Fannie Mae and Freddie Mac workbooks
      And the active compliance source identifies one of those workbooks
      When the runtime loads governed constraint rows
      Then it reads rows only from the active workbook and its configured worksheet

  @IT-60R2
  Rule: Preserve governed source values and identifiers

    @IT-60R2S1
    Scenario: Preserve a leading-zero source identifier as text
      Given a governed workbook row has an identifier with leading zeroes
      When the runtime reads that row
      Then the identifier is returned as text
      And its leading zeroes are preserved exactly as governed by the workbook

    @IT-60R2S2
    Scenario: Preserve source values used to identify a governed representation
      Given a governed workbook row has a configured representation binding
      When the runtime reads the row and checks the binding definition
      Then it compares the exact workbook-derived source values
      And it does not convert identifier fields to numbers

    @IT-60R3
  Rule: Production evaluators use workbook-derived governed rows

    @IT-60R3S1
    Scenario: Load supported required-data rules from the active workbook
      Given the active workbook contains rows for supported required-data rules
      When the required-data rule set is loaded
      Then each supported rule is matched to its row from the active workbook
      And a CSV-derived value does not cause a governed representation mismatch

    @IT-60R3S2
    Scenario: Preserve workbook source values in validation findings
      Given a required-data rule is loaded from the active workbook
      When that rule produces a validation finding
      Then the finding uses the governed identifier and message from the workbook row
      And its source trace identifies the configured workbook and worksheet