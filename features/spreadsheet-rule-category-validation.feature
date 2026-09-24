@IT-1
Feature: Validate appraisal data against governed rule categories
  Apply the spreadsheet rules selected for the first release
  and report findings that identify the violated source rule.

  Background:
    Given the governed spreadsheet rule inventory is available
    And the first-release rule selection is defined
    And validation uses each selected row's applicability, XML context, and rule logic
    And each finding identifies the source row, Rule ID, severity, and affected XML context

  @IT-1R1
  Rule: Other conditional or scoped requirements follow their governed applicability

    @IT-1R1S1 @category_other_conditional_scoped
    Scenario: Enforce a requirement in its applicable condition and scope
      Given a selected conditional or scoped required-data row
      And an XML fixture with the dependent data absent
      When I validate with the governed applicability conditions unsatisfied
      Then no missing-data finding is reported for that row
      When I satisfy those conditions and validate again
      Then a missing-data finding is reported for that row
      When I supply the required dependent value and validate again
      Then no finding is reported for that row

  @IT-1R2
  Rule: A single equality trigger controls conditional required data

    @IT-1R2S1 @category_single_equality_conditional
    Scenario: Require data only when the equality condition is satisfied
      Given a selected conditional required-data row with a single equality trigger
      And an applicable XML fixture with the dependent data absent
      When I validate with the trigger set to a governed nonmatching value
      Then no missing-data finding is reported for that row
      When I validate with the trigger set to the governed matching value
      Then a missing-data finding is reported for that row
      When I supply the required dependent value and validate again
      Then no finding is reported for that row

  @IT-1R3
  Rule: Required containers or collections must exist

    @IT-1R3S1 @category_required_structures
    Scenario: Detect an absent required structure
      Given a selected required-container or required-collection row
      And an applicable XML fixture containing the required structure
      When I validate the fixture
      Then no finding is reported for that row
      When I remove the required structure and validate again
      Then a missing-structure finding is reported for that row

  @IT-1R4
  Rule: Unconditional required data must be supplied

    @IT-1R4S1 @category_unconditional_required
    Scenario: Detect absent required data
      Given a selected unconditional required-data row
      And an applicable XML fixture containing the required value
      When I validate the fixture
      Then no finding is reported for that row
      When I remove the required value and validate again
      Then a missing-data finding is reported for that row

  @IT-1R5
  Rule: Occurrences must satisfy governed uniqueness or cardinality requirements

    @IT-1R5S1 @category_uniqueness_cardinality
    Scenario: Reject a prohibited duplicate or occurrence count
      Given a selected uniqueness or cardinality row
      And an applicable XML fixture satisfying that row
      When I validate the fixture
      Then no finding is reported for that row
      When I change the occurrences to violate the governed requirement and validate again
      Then a uniqueness or cardinality finding is reported for that row

  @IT-1R6
  Rule: Numeric values must satisfy governed bounds

    @IT-1R6S1 @category_numeric_bounds
    Scenario: Reject a numeric value outside its allowed bounds
      Given a selected numeric-bound row
      And an applicable XML fixture containing an allowed numeric value
      When I validate the fixture
      Then no finding is reported for that row
      When I replace the value with one outside the governed bounds and validate again
      Then a numeric-bound finding is reported for that row

  @IT-1R7
  Rule: Values must satisfy governed format, precision, or text-length restrictions

    @IT-1R7S1 @category_format_precision_length
    Scenario: Reject a value that violates its representation restriction
      Given a selected format, precision, or text-length row
      And an applicable XML fixture containing a value allowed by that row
      When I validate the fixture
      Then no finding is reported for that row
      When I replace the value with one violating the selected restriction and validate again
      Then a representation finding is reported for that row

  @IT-1R8
  Rule: Required data must be present within an existing applicable context

    @IT-1R8S1 @category_existing_context_required
    Scenario: Detect missing data inside an existing context
      Given a selected row requiring data within an existing XML context
      And an applicable XML fixture containing that context and its required value
      When I validate the fixture
      Then no finding is reported for that row
      When I remove the required value while retaining its context and validate again
      Then a missing-data finding identifies that context

  @IT-1R9
  Rule: Relationships and references must satisfy governed integrity requirements

    @IT-1R9S1 @category_relationship_reference_integrity
    Scenario: Reject an invalid relationship or reference
      Given a selected relationship or reference-integrity row
      And an applicable XML fixture containing a relationship satisfying that row
      When I validate the fixture
      Then no finding is reported for that row
      When I change the relationship or reference to violate the governed requirement and validate again
      Then a relationship or reference-integrity finding is reported for that row

  @IT-1R10
  Rule: Values and related fields must satisfy governed consistency requirements

    @IT-1R10S1 @category_value_cross_field_consistency
    Scenario: Reject inconsistent field values
      Given a selected value or cross-field consistency row
      And an applicable XML fixture containing values satisfying that row
      When I validate the fixture
      Then no finding is reported for that row
      When I change a participating value to violate the governed requirement and validate again
      Then a consistency finding is reported for that row


  @IT-1R11
  Rule: Dates must satisfy governed chronological requirements

    @IT-1R11S1 @category_date_chronology
    Scenario: Reject a prohibited date relationship
      Given a selected date or chronology row
      And an applicable XML fixture containing dates satisfying that row
      When I validate the fixture
      Then no finding is reported for that row
      When I change a date to violate the governed chronological requirement and validate again
      Then a chronology finding is reported for that row


  @IT-1R12
  Rule: Alternative or mutually exclusive data must satisfy the governed combination

    @IT-1R12S1 @category_alternative_mutually_exclusive
    Scenario: Reject a disallowed combination of data
      Given a selected alternative-data or mutual-exclusion row
      And an applicable XML fixture containing a combination allowed by that row
      When I validate the fixture
      Then no finding is reported for that row
      When I change the data to a combination prohibited by that row and validate again
      Then a combination finding is reported for that row

  @IT-1R13
  Rule: Aggregates and related records must satisfy governed consistency requirements

    @IT-1R13S1 @category_aggregate_cross_record_consistency
    Scenario: Detect an aggregate or cross-record inconsistency
      Given a selected aggregate or cross-record consistency row
      And an applicable XML fixture containing records satisfying that row
      When I validate the fixture
      Then no finding is reported for that row
      When I change a participating record to violate the governed requirement and validate again
      Then an aggregate or cross-record finding is reported for that row