Feature: IT-36 — Numeric/format validation
  Ranges, counts, dates, formats and similar deterministic tests

  Background:
    Given the selected MVP constraint inventory is available
    And each selected numeric/format row identifies its source row ID, governed XML context, and restriction
    And the limits, boundary rules, units, date rules, or format definition needed by each supported row are available

  # IT-36 — Apply reusable numeric and format checks configured by inventory data.
  # Implement only the operators needed by the selected MVP rows.
  # Reuse schema validation where it already enforces the same restriction.
  # Required-data checks remain in IT-33 and IT-34; value/domain checks remain in IT-35.

  @IT-36R1
  Rule: Check numeric values and counts against their configured limits

    @IT-36R1S1
    Scenario: Evaluate a supported numeric or count restriction
      Given a selected constraint defines a numeric range, count, or precision restriction
      When the shared evaluator checks the applicable value or occurrence count
      Then values satisfying the configured restriction produce no finding for that constraint
      And values violating the restriction produce one finding for that constraint and affected context occurrence
      And lower and upper boundaries follow the configured inclusive or exclusive rules
      And decimal comparisons preserve the precision required by the governed restriction
      And a supplied count is checked for integrality and its configured limits
      And an occurrence count includes only the elements selected by the governed context
      And a supplied zero is evaluated against the restriction rather than treated as missing
      And values are not rounded, truncated, or converted between units unless the governed rule specifies it

  @IT-36R2
  Rule: Check dates and text formats against explicit governed definitions

    @IT-36R2S1
    Scenario: Evaluate a supported date or format restriction
      Given a selected constraint defines a date or text format restriction
      When the shared evaluator checks an applicable supplied value
      Then a value satisfying the restriction produces no finding for that constraint
      And a value violating the restriction produces one finding for that constraint and element occurrence
      And date validation checks both the required representation and calendar validity
      And pattern matching follows the configured whole-value or partial-match semantics
      And whitespace, case, and timezone handling follow the governed definition
      And locale-dependent parsing does not change the result
      And values are not silently rewritten into a valid format

  @IT-36R3
  Rule: Return consistent results without guessing rule semantics

    @IT-36R3S1
    Scenario: Evaluate applicable contexts and produce actionable findings
      Given a selected numeric/format constraint has a complete supported configuration
      When the evaluator resolves its context using namespace-qualified element identities
      Then each applicable occurrence is checked independently
      And scalar absence, blank content, or nil content is left to the applicable required-data checks
      And an empty selection for an occurrence-count rule is evaluated as a count of zero
      And each finding preserves the source row ID, source rule ID, governed severity, and affected XML context
      And each finding identifies the rejected value or count and the expected restriction
      And a nonblank value that cannot be parsed is identified as invalid rather than replaced with zero or a default date
      And a parsing failure already reported by IT-35 or schema-backed validation does not produce a duplicate finding for the same constraint and occurrence
      And unchanged inputs produce the same findings in the same order

    @IT-36R3S2
    Scenario: Identify a restriction that cannot be evaluated reliably
      Given a selected row has an unsupported operator or unresolved context, limits, units, date semantics, or format definition
      When the evaluator processes that row
      Then an evaluation exception identifies the source row ID and the reason
      And the row is not reported as passing
      And missing rule semantics are not inferred from element names or fixture values
      And other supported rows continue to be evaluated

  @IT-36R4
  Rule: Prove supported numeric and format behavior with focused PyTest coverage

    @IT-36R4S1
    Scenario: Verify valid values, invalid values, and boundaries through the shared evaluator
      Given each supported selected numeric/format row is mapped to appropriate test cases
      When parameterized PyTest tests exercise the configured restrictions
      Then numeric cases check each configured boundary and representable values immediately inside and outside it
      And count cases check zero, permitted counts, and counts violating configured limits
      And precision cases check permitted precision and excess precision where restricted
      And date cases include valid dates, impossible calendar dates, and applicable leap-year boundaries
      And format cases include matching values and controlled nonmatching values
      And permitted values produce no findings for the tested constraints
      And rejected values produce the expected findings by source row ID and affected occurrence
      And separate context occurrences are verified independently
      And existing XML fixtures are reused when they exercise the intended restriction
      And missing-data fixtures alone are not counted as numeric/format coverage
      And only missing cases are added as controlled variations of the source XML
      And unsupported rows and coverage gaps are identified explicitly
      And the existing regression suite remains green
