Feature: Project a UAD 3.6 XML instance into RDF

  As a compliance service operator
  I want a UAD 3.6 XML appraisal projected into a canonical RDF graph
  So that business rules can be evaluated independently of the XML structure

  Background:
    Given the UAD 3.6 ontology and projection rules are loaded

  Scenario: Project a valid appraisal instance
    Given a valid UAD 3.6 XML appraisal
    When the XML-to-RDF projection runs
    Then the result is an RDF instance graph
    And each projected resource has a deterministic IRI
    And XML element values are represented as RDF facts
    And XML attribute values are represented as RDF facts
    And repeating XML structures produce distinct RDF resources
    And XLink relationships are represented as RDF predicates
    And RDF literals use the appropriate datatypes
    And every projected fact is traceable to its source XML location

  Scenario: Produce the same graph for repeated projections
    Given the same valid UAD 3.6 XML appraisal
    When the XML-to-RDF projection runs more than once
    Then each run produces an isomorphic RDF graph
    And the same source nodes receive the same IRIs

  Scenario: Match the expected RDF projection
    Given a valid UAD 3.6 XML appraisal
    And an approved expected RDF graph for that appraisal
    When the XML-to-RDF projection runs
    Then the projected graph is isomorphic to the expected RDF graph

  Scenario: Reject XML that cannot be projected safely
    Given a UAD XML document containing an unsupported or ambiguous construct
    When the XML-to-RDF projection runs
    Then the projection fails
    And the result identifies the source location
    And no guessed semantic relationship is created