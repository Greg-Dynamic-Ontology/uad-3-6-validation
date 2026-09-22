Feature: Execute governed constraint-production batches from the Batch Knowledge Graph
  As an OTDD constraint-production process
  I want the governed Batch Knowledge Graph to drive batch execution
  So that governed constraint rows can be materialized, processed, and recorded
  without manually identifying the members of each batch

  Background:
    Given the governed Batch Knowledge Graph is stored at the configured location
    And the Batch Knowledge Graph identifies each planned constraint-production batch
    And each batch identifies its governed workbook, worksheet, and cell range
    And column A of the governed worksheet contains the governed Unique ID for each source constraint
    And batch execution produces a persistent RDF batch-results graph on disk

  # IT-35 — Execute governed constraint-production batches
  # configured location "ontologies/constraints/batches/governed-batch-knowledge-graph.ttl"

  @IT-35R1
  Rule: Materialize the governed members of a batch before constraint production begins

    @IT-35R1S1
    Scenario: Write the governed Unique IDs for a batch into the batch-results RDF graph
      Given a batch is selected from the governed Batch Knowledge Graph
      And the selected batch identifies a governed workbook, worksheet, and cell range
      When the batch source range is read
      Then each governed Unique ID in column A of the selected range is read
      And each governed Unique ID is represented in the batch-results RDF graph
      And each represented Unique ID is associated with the selected batch
      And the number of represented Unique IDs equals the intended constraint count for the batch
      And the batch-results RDF graph is written to disk

  @IT-35R2
  Rule: Keep the persistent batch-results graph synchronized with constraint production

    @IT-35R2S1
    Scenario: Add or overwrite constraint knowledge and persist batch-run knowledge as processing proceeds
      Given the governed Unique IDs for the selected batch have been materialized in the batch-results RDF graph
      And constraint production is executing for the selected batch
      When knowledge for a governed constraint is produced or changed
      Then the current constraint representation in the batch-results RDF graph is added or overwritten
      And the batch-results RDF graph records the current construction stage for that constraint
      And the batch-results RDF graph records whether the current stage is RED, GREEN, or an exception
      And the batch-results RDF graph records any exception reason associated with that constraint
      And the batch-results RDF graph records the current status of the selected batch
      And the updated batch-results RDF graph is written to disk before processing continues
      And the disk copy of the batch-results RDF graph reflects the latest completed production event
