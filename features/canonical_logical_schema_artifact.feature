Feature: Govern the canonical Logical Schema artifact

  The Logical Schema Model may be persisted as an RDF/Turtle milestone
  artifact for inspection, regression analysis, interchange, and restart.
  Routine automated tests must not modify that committed artifact.

  @IT-8R1
  Rule: The canonical artifact is generated deliberately

    @IT-8R1S1
    Scenario: Routine tests do not modify the canonical artifact
      Given the canonical Logical Schema artifact is committed
      When its serialization behavior is tested
      Then the test artifact is written to a temporary location
      And the temporary artifact parses as a valid RDF graph
      And the temporary artifact represents a Logical Schema Model
      And the committed canonical artifact remains unchanged

    @IT-8R1S2
    Scenario: The canonical artifact contains portable source references
      Given the complete UAD Logical Schema Model
      When the canonical artifact is generated
      Then source document references are project-relative or governed IRIs
      And the artifact contains no machine-specific absolute paths
      And the artifact contains no user-specific directory names
