Feature: Modular schema loading

  As the XML Schema loader evolves
  I want implementation responsibilities separated by XML Schema concept
  So that new schema concepts can be added without increasing implementation complexity.

  Background:
    Given an XML Schema document

  Scenario: SchemaLoader remains the public entry point
    When the schema is loaded
    Then a SchemaModel is returned

  Scenario: Refactoring preserves loader behavior
    When the implementation is modularized
    Then the resulting SchemaModel is unchanged

  Scenario: XML Schema concepts have focused implementations
    Then namespace loading is implemented independently
    And QName resolution is implemented independently
    And simple type loading is implemented independently
    And complex type loading is implemented independently

  Scenario: New XML Schema concepts are added modularly
    Given support for an additional XML Schema construct
    When that support is implemented
    Then a new focused module may be added
    And existing modules need not grow in unrelated responsibilities

  Rule: Modular schema loading

    The schema loader may be reorganized into focused implementation
    modules without changing its observable behavior.

    Scenario: SchemaLoader remains the public entry point
      Given a supported XML Schema document
      When the schema is loaded through SchemaLoader
      Then a Logical Schema Model is returned

    Scenario: Modularization preserves observable behavior
      Given the schema loader has been modularized
      When the same XML Schema document is loaded
      Then the resulting Logical Schema Model is unchanged

    Scenario: Responsibilities are organized by XML Schema concept
      Given the modular schema loading implementation
      Then namespace handling is implemented independently
      And QName resolution is implemented independently
      And simple type loading is implemented independently
      And complex type loading is implemented independently

    Scenario: New XML Schema concepts can be added modularly
      Given support for an additional XML Schema construct
      When the implementation is extended
      Then a focused loading module may be added
      And unrelated loading modules need not be modified