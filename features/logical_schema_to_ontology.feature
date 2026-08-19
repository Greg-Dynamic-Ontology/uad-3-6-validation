Feature: Project the UAD Logical Schema Model into the shared MISMO ontology

  As the UAD 3.6 validation engine
  I want to project the Logical Schema Model into an RDF ontology
  So that schema meaning can be queried, validated, measured, and reused
  as knowledge

  @IT-7R1
  Rule: Project schema components

    @IT-7R1S1
    Scenario: A named complex type projects to an OWL class
      Given a Logical Schema Model containing a named complex type
      When the model is projected to an ontology
      Then the ontology contains an OWL class representing the complex type

    @IT-7R1S2
    Scenario: A named simple type projects to an ontology resource
      Given a Logical Schema Model containing a named simple type
      When the model is projected to an ontology
      Then the ontology contains a resource representing the simple type

    @IT-7R1S3
    Scenario: A global element projects to an RDF property
      Given a Logical Schema Model containing a global element declaration
      When the model is projected to an ontology
      Then the ontology contains an RDF property representing the element

    @IT-7R1S4
    Scenario: A global attribute projects to an RDF property
      Given a Logical Schema Model containing a global attribute declaration
      When the model is projected to an ontology
      Then the ontology contains an RDF property representing the attribute

  @IT-7R2
  Rule: Preserve semantic relationships

    @IT-7R2S1
    Scenario: An element type projects to a property range
      Given a global element declaration with a declared type
      When the model is projected to an ontology
      Then the projected property has a range corresponding to the declared type

    @IT-7R2S2
    Scenario: A complex type base projects to a subclass relationship
      Given a complex type derived from another complex type
      When the model is projected to an ontology
      Then the projected class is a subclass of the projected base class

    @IT-7R2S3
    Scenario: A simple type restriction preserves its base type
      Given a simple type derived by restriction
      When the model is projected to an ontology
      Then the projected resource identifies the restriction base

    @IT-7R2S4
    Scenario: Enumeration values project to a controlled vocabulary
      Given a simple type containing enumeration values
      When the model is projected to an ontology
      Then each enumeration value appears in the projected controlled vocabulary

  @IT-7R3
  Rule: Produce deterministic identifiers

    @IT-7R3S1
    Scenario: Projection uses the governed shared MISMO ontology namespace
      Given a UAD Logical Schema Model with a target namespace
      When the model is projected to an ontology
      Then every projected domain ontology term uses an IRI in the governed shared MISMO ontology namespace
      And each projected schema component uses an IRI in the governed UAD schema-resource namespace
      And each projected ontology term identifies its originating schema component
      And the source target namespace is preserved as source identity and provenance
      And no project-created term is minted under an uncontrolled source namespace
      And any schema component without a governed MISMO mapping remains explicitly unresolved

    @IT-7R3S2
    Scenario: Missing source namespace does not change ontology authority
      Given a UAD Logical Schema Model without a target namespace
      When the model is projected to an ontology
      Then every projected domain ontology term uses an IRI in the governed shared MISMO ontology namespace
      And the missing source namespace remains visible in the ontology-projection reconciliation

    @IT-7R3S3
    Scenario: Repeated projection produces the same IRIs
      Given the same Logical Schema Model
      When the model is projected multiple times
      Then each projection produces identical IRIs

  @IT-7R4
  Rule: Preserve traceability

    @IT-7R4S1
    Scenario: Projection preserves traceability
      Given a component in the Logical Schema Model
      When the component is projected to an ontology resource
      Then the ontology resource records the originating schema component
      And the source schema location is preserved when available

  @IT-7R5
  Rule: Produce valid RDF

    @IT-7R5S1
    Scenario: The projected ontology is valid RDF
      Given a Logical Schema Model
      When the model is projected to Turtle
      Then the generated Turtle parses as a valid RDF graph

    @IT-7R5S2
    Scenario: Duplicate projections do not create duplicate triples
      Given a Logical Schema Model containing repeated references to the same component
      When the model is projected to an ontology
      Then the resulting RDF graph contains only one copy of each triple

  @IT-7R6
  Rule: The complete UAD Logical Schema Model reconciles with the ontology

    @IT-7R6S1
    Scenario: Project every represented UAD schema component
      Given the complete UAD Logical Schema Model has been loaded
      When the model is projected into the governed shared MISMO ontology
      Then every schema component selected for representation identifies an authoritative RDF term
      And every projected RDF term identifies its originating schema component
      And every schema component occurrence has exactly one ontology-projection disposition
      And every deliberately excluded occurrence identifies its governing decision
      And no selected schema component silently disappears

    @IT-7R6S2
    Scenario: Projected appraisal terms use the governed shared MISMO ontology
      Given the governed shared MISMO ontology has been generated
      And a UAD XML appraisal has been loaded
      When the appraisal is projected into RDF
      Then every instance class is declared by the governed shared MISMO ontology or a documented external vocabulary
      And every instance property is declared by the governed shared MISMO ontology or a documented external vocabulary
      And every value governed by a schema datatype uses its projected RDF datatype
      And every value governed by a controlled vocabulary uses its projected vocabulary term
      And every unresolved instance term remains visible

    @IT-7R6S3
    Scenario: Repeated complete ontology projection is deterministic
      Given the complete UAD Logical Schema Model has been loaded
      When the model is projected into the governed shared MISMO ontology more than once
      Then each projection produces an equivalent ontology graph
      And each projection produces the same schema-to-ontology reconciliation
