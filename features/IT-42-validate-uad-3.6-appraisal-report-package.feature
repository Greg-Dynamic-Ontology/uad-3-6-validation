@IT-42
Feature: Validate a UAD 3.6 appraisal report package

  As a lender, appraisal software provider, or review platform
  I want to submit a UAD 3.6 appraisal report package for validation
  So that I can identify specification, mapping, and rule compliance issues before delivery

  Background:
    Given the UAD 3.6 schema model has been loaded
    And Appendix A mapping and XLink requirements have been loaded
    And Appendix H validation rules have been loaded

  @IT-42R1
  Rule: Validate a submitted UAD 3.6 appraisal report package

    The service evaluates the package against the governed schema,
    mappings, controlled values, datatypes, and applicable Appendix H rules.

    @IT-42R1S1
    Scenario: Validate XML structure
      Given a UAD 3.6 appraisal XML report package
      When the client submits the package to the validation API
      Then the service validates the XML against the GSE trimmed schema
      And the response identifies structural validation errors
      And each structural error identifies the affected XML location
      And each structural error identifies the governing schema component

    @IT-42R1S2
    Scenario: Convert XML instance nodes to graph resources
      Given a structurally readable UAD 3.6 appraisal XML report package
      When the service processes the package
      Then each addressable XML instance node is represented as a graph resource
      And each graph resource has a stable IRI
      And each graph resource retains its source XML location
      And XML IDs are preserved when present

    @IT-42R1S3
    Scenario: Validate XLink relationships
      Given a UAD 3.6 appraisal XML report package containing XLink relationships
      When the service evaluates Appendix A mapping requirements
      Then each XLink subject is resolved to a graph resource IRI
      And each XLink object is resolved to a graph resource IRI
      And each XLink predicate is resolved to a governed predicate IRI
      And invalid, missing, or disallowed relationships are reported as findings

    @IT-42R1S4
    Scenario: Validate controlled values and datatypes
      Given a UAD 3.6 appraisal XML report package
      When the service evaluates schema validation elements
      Then datatype violations are reported as findings
      And enumeration violations are reported as findings
      And each finding identifies the observed value
      And each finding identifies the expected datatype or controlled value set

    @IT-42R1S5
    Scenario: Validate Appendix H rules
      Given a UAD 3.6 appraisal XML report package
      When the service evaluates Appendix H rules
      Then each applicable rule is evaluated
      And failed rules are reported as findings
      And each finding identifies the rule identifier
      And each finding identifies the affected XML or graph resource location
      And each finding identifies whether the rule applies to Fannie Mae, Freddie Mac, or both

    @IT-42R1S6
    Scenario: Apply both GSE rule sets by default
      Given a UAD 3.6 appraisal XML report package
      And the client does not specify the loan delivery GSE
      When the client submits the package to the validation API
      Then the service evaluates both Fannie Mae and Freddie Mac requirements
      And the response distinguishes Fannie-only, Freddie-only, and shared findings