@CO-1 @change-order @constraint-production
Feature: Switch constraint production to the configured GSE source
  As the governed constraint-production process
  I want to use the active GSE workbook selected in configuration.ttl
  So that constraint production reads from the published Fannie Mae or Freddie Mac source

  Background:
    Given IT-50 normalization is complete
    And IT-51 governed RDF exchange is complete
    And the change order declares its expected current state and target state

  @CO-1R1
  Rule: Apply a change order only when the current state matches its expected state

    @CO-1R1S1
    Scenario: Apply the source change from the expected project state
      Given IT-50 reads governed constraint rows from data-constraints.csv
      And configuration.ttl identifies both GSE source workbooks
      And configuration.ttl selects exactly one active compliance source
      When the change order is executed
      Then the change order verifies the expected state before changing project artifacts
      And IT-50 resolves its source workbook from the active compliance source in configuration.ttl
      And IT-50 reads the configured rule-data worksheet
      And IT-50 and IT-51 retain their completed behavior and governed RDF contracts

    @CO-1R1S2
    Scenario: Do nothing when the change order is executed out of order
      Given the project state does not match the change order's expected current state
      When the change order is executed
      Then no project artifacts are changed
      And the change order records that its precondition was not met

    @CO-1R1S3
    Scenario: Do nothing when the change order is executed more than once
      Given the change order has already moved the project to its target state
      When the change order is executed again
      Then no project artifacts are changed
      And the project remains in the target state

  @CO-1R2
  Rule: Read constraint rows from the single active configured GSE source

    @CO-1R2S1
    Scenario: Read a governed constraint row from the active workbook
      Given configuration.ttl selects one active compliance source
      And the active source identifies a workbook path and rule-data worksheet
      And the requested governed Unique ID identifies exactly one row on that worksheet
      When IT-50 reads the selected constraint
      Then the source knowledge is read directly from that workbook row
      And the governed Unique ID and source location are preserved
      And the unselected workbook is not used for the read

    @CO-1R2S2
    Scenario: Reject configuration without exactly one active source
      Given configuration.ttl identifies zero or more than one active compliance source
      When IT-50 resolves its governed source
      Then source resolution is rejected
      And no normalized constraint is produced
      And the rejection identifies the invalid active-source selection

    @CO-1R2S3
    Scenario: Reject a requested Unique ID that does not identify exactly one workbook row
      Given configuration.ttl selects one active compliance source
      And the requested governed Unique ID identifies zero or multiple rows on its rule-data worksheet
      When IT-50 reads the selected constraint
      Then source-row selection is rejected
      And no normalized constraint is produced
      And the rejection identifies the non-unique source-row selection