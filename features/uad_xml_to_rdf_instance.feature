Feature: Project a UAD XML appraisal into an RDF instance graph

  Rule: Every XML occurrence receives a projection disposition

    @IT-6R1S1
    Scenario: Inventory a real UAD appraisal for RDF projection
      Given a UAD XML appraisal has been loaded
      When its XML occurrences are inventoried
      Then every element occurrence is recorded
      And every attribute occurrence is recorded
      And every occurrence records its source location

    @IT-6R1S2
    Scenario: Reconcile the XML appraisal with its RDF projection
      Given a UAD XML appraisal has been loaded
      When the appraisal is projected into RDF
      Then every inventoried XML occurrence has exactly one projection disposition
      And every represented occurrence identifies its RDF term
      And every excluded occurrence identifies its governing decision
      And no occurrence silently disappears
