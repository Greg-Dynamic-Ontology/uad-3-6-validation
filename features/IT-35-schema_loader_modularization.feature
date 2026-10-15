@IT-35
Feature: Modular schema loading

  As the XML Schema loader evolves
  I want implementation responsibilities separated by XML Schema concept
  So that new schema concepts can be added without increasing implementation complexity.

  Background:
    Given an XML Schema document

  @IT-35R1
  Rule: Modular schema loading

    The schema loader may be reorganized into focused implementation
    modules without changing its observable behavior.

    @IT-35R1S1
    Scenario: SchemaLoader remains the public entry point
      Given a supported XML Schema document
      When the schema is loaded through SchemaLoader
      Then a Logical Schema Model is returned

    @IT-35R1S2
    Scenario: Modularization preserves observable behavior
      Given the schema loader has been modularized
      When the same XML Schema document is loaded
      Then the resulting Logical Schema Model is unchanged

    @IT-35R1S3
    Scenario: Responsibilities are organized by XML Schema concept
      Given the modular schema loading implementation
      Then namespace handling is implemented independently
      And QName resolution is implemented independently
      And simple type loading is implemented independently
      And complex type loading is implemented independently

    @IT-35R1S4
    Scenario: New XML Schema concepts can be added modularly
      Given support for an additional XML Schema construct
      When the implementation is extended
      Then a focused loading module may be added
      And unrelated loading modules need not be modified