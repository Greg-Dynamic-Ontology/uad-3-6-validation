Feature: Project Logical Schema Model to Ontology
  As the UAD 3.6 validation engine
  I want to project the Logical Schema Model into an RDF ontology
  So that schema meaning can be queried, validated, measured, and reused as knowledge

  Rule: Project schema components

    Scenario: A named complex type projects to an OWL class
      Given a Logical Schema Model containing a named complex type
      When the model is projected to an ontology
      Then the ontology contains an OWL class representing the complex type

    Scenario: A named simple type projects to an ontology resource
      Given a Logical Schema Model containing a named simple type
      When the model is projected to an ontology
      Then the ontology contains a resource representing the simple type

    Scenario: A global element projects to an RDF property
      Given a Logical Schema Model containing a global element declaration
      When the model is projected to an ontology
      Then the ontology contains an RDF property representing the element

    Scenario: A global attribute projects to an RDF property
      Given a Logical Schema Model containing a global attribute declaration
      When the model is projected to an ontology
      Then the ontology contains an RDF property representing the attribute

  Rule: Preserve semantic relationships

    Scenario: An element type projects to a property range
      Given a global element declaration with a declared type
      When the model is projected to an ontology
      Then the projected property has a range corresponding to the declared type

    Scenario: A complex type base projects to a subclass relationship
      Given a complex type derived from another complex type
      When the model is projected to an ontology
      Then the projected class is a subclass of the projected base class

    Scenario: A simple type restriction preserves its base type
      Given a simple type derived by restriction
      When the model is projected to an ontology
      Then the projected resource identifies the restriction base

    Scenario: Enumeration values project to a controlled vocabulary
      Given a simple type containing enumeration values
      When the model is projected to an ontology
      Then each enumeration value appears in the projected controlled vocabulary

  Rule: Produce deterministic identifiers

    Scenario: Projection uses the schema target namespace
      Given a Logical Schema Model with a target namespace
      When the model is projected to an ontology
      Then projected resources use IRIs derived from the target namespace

    Scenario: Projection uses the fallback namespace when no target namespace exists
      Given a Logical Schema Model without a target namespace
      When the model is projected to an ontology
      Then projected resources use the configured fallback namespace

    Scenario: Repeated projection produces the same IRIs
      Given the same Logical Schema Model
      When the model is projected multiple times
      Then each projection produces identical IRIs

  Rule: Preserve traceability

    Scenario: Projection preserves traceability
      Given a component in the Logical Schema Model
      When the component is projected to an ontology resource
      Then the ontology resource records the originating schema component
      And the source schema location is preserved when available

  Rule: Produce valid RDF

    Scenario: The projected ontology is valid RDF
      Given a Logical Schema Model
      When the model is projected to Turtle
      Then the generated Turtle parses as a valid RDF graph

    Scenario: Duplicate projections do not create duplicate triples
      Given a Logical Schema Model containing repeated references to the same component
      When the model is projected to an ontology
      Then the resulting RDF graph contains only one copy of each triple