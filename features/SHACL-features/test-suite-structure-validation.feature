@ITF-1
Feature: Validate the structure of governed RDF test suites
  Ensure the test inventory has the required number of cases
  before using it to assess appraisal validation.

  @ITF-1R1
  Rule: The single-equality suite contains exactly 174 distinct cases

  @ITF-1R1S1 @Check_the_single-equality_case_count
  Scenario: Check the single-equality case count
      Given the single-equality RDF test suite is selected
      When its structure is validated using SHACL
      Then it conforms only if it links to exactly 174 distinct cases
      And an absent suite is reported as a violation
      And a case-count violation identifies the suite and required count