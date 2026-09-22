Feature: IT-35 — Value/domain validation
  Enumerations, permitted values, indicators, types, etc.

  Background:
    Given the selected MVP constraint inventory is available
    And each selected value/domain row identifies its source row ID, governed XML context, and value restriction
    And the governed permitted values, indicator values, or datatype definition are available for each supported row

  # IT-35 — Apply reusable value/domain checks configured by inventory data.
  # Reuse schema validation where the XSD already enforces the same restriction.
  # Required-data checks remain in IT-33 and IT-34; numeric ranges and formats remain in IT-36.

  @IT-35R1
  Rule: Check supplied values against their governed domain

    @IT-35R1S1
    Scenario: Accept a permitted value
      Given a selected constraint defines a supported enumeration, permitted-value set, indicator domain, or datatype
      And an applicable element contains a supplied value
      When the shared value/domain evaluator checks that value
      Then a value conforming to the governed restriction produces no finding for that constraint
      And comparison follows the governed case, whitespace, and datatype rules
      And supplied zero and false values are evaluated as values rather than treated as missing

    @IT-35R1S2
    Scenario: Report a value outside the permitted domain
      Given an applicable element contains a value that violates a selected supported restriction
      When the shared value/domain evaluator checks that value
      Then one finding is produced for that constraint and element occurrence
      And the finding preserves the source row ID, source rule ID, governed severity, and affected XML context
      And the finding identifies the rejected value and explains the permitted domain or required type
      And the evaluator does not silently correct, replace, or coerce the value into compliance
      And an existing schema result is reused only when it can be traced to the same governed constraint and occurrence
      And schema mechanics do not replace governed finding identity or meaning

  @IT-35R2
  Rule: Apply each restriction only in its governed context

    @IT-35R2S1
    Scenario: Check applicable occurrences independently
      Given a selected value/domain constraint applies to multiple XML element occurrences
      When the evaluator resolves its configured context using namespace-qualified element identities
      Then each applicable supplied value is checked independently
      And a valid value in one occurrence does not mask an invalid value in another
      And absent, blank, or nil data is handled by the applicable required-data checks without a duplicate missing-data finding from this evaluator
      And the absence of a value/domain finding does not establish required-data conformance
      And unchanged inputs produce the same findings in the same order

    @IT-35R2S2
    Scenario: Identify a restriction that cannot be evaluated
      Given a selected row has an unsupported restriction or unresolved domain, datatype, or applicability
      When the evaluator processes that row
      Then an evaluation exception identifies the source row ID and the reason
      And the row is not reported as passing
      And permitted values and datatype semantics are not guessed from fixture contents or element names
      And other supported rows continue to be evaluated

  @IT-35R3
  Rule: Prove the supported value/domain rows with focused PyTest coverage

    @IT-35R3S1
    Scenario: Verify permitted and rejected values through the shared evaluator
      Given each supported selected value/domain row is mapped to appropriate test cases
      When parameterized PyTest tests evaluate permitted and prohibited values in the governed context
      Then permitted values produce no value/domain findings for the tested constraints
      And prohibited values produce the expected findings by source row ID and affected occurrence
      And the cases cover the supported enumeration, indicator, and datatype behaviors
      And the cases check governed case and whitespace behavior where applicable
      And the cases verify that separate occurrences are evaluated independently
      And schema-backed checks produce no duplicate finding for the same constraint and occurrence
      And existing XML fixtures are reused when they exercise the intended value restriction
      And missing-data fixtures alone are not counted as value/domain coverage
      And only missing cases are added as controlled value changes to the source XML
      And unsupported rows and coverage gaps are identified explicitly
      And the existing regression suite remains green
