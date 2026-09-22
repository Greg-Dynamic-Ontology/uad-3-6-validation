Feature: Conditional-required validation
  Implement the reusable conditional requirement mechanism and exercise all applicable inventory rows.

  Background:
    Given the selected MVP constraint inventory is available
    And each conditional-required row identifies its source row ID, triggering condition, required data, and applicable XML context
    And the required-data evaluator from IT-33 is available

  # IT-34 — Add condition evaluation to the existing required-data capability.
  # Inventory data supplies the conditions and requirements; reuse the same evaluator across rows.
  # Reuse existing XML fixtures wherever they exercise the applicable condition.

  @IT-34R1
  Rule: Require the governed data only when its condition is satisfied

    @IT-34R1S1
    Scenario: Enforce a requirement when its condition is true
      Given a selected conditional-required constraint has a supported condition
      When that condition is true in an applicable XML context
      Then the IT-33 required-data evaluator checks the required data in that context
      And missing, blank, or nil required scalar data produces one finding for that row and context occurrence
      And supplied required data produces no missing-data finding
      And the finding preserves the source row ID, source rule ID, governed severity, and affected XML context
      And the finding explains the condition and which required data must be supplied

    @IT-34R1S2
    Scenario: Do not require the data when its condition is false
      Given a selected conditional-required constraint has a supported condition
      When that condition is false in an applicable XML context
      Then absent dependent data produces no finding for that constraint
      And unconditional requirements for the same data remain independently applicable

  @IT-34R2
  Rule: Evaluate conditions within the governed scope without guessing unsupported behavior

    @IT-34R2S1
    Scenario: Evaluate each applicable occurrence independently
      Given a conditional-required constraint applies to multiple XML context occurrences
      When the evaluator checks the condition for each occurrence
      Then condition values are resolved using the inventory's governed paths and namespace-qualified element identities
      And data from another occurrence does not satisfy the condition or requirement unless the rule explicitly references it
      And each occurrence whose condition is true receives its own required-data check
      And repeated evaluation with unchanged inputs produces the same findings in the same order

    @IT-34R2S2
    Scenario: Identify a condition that cannot be evaluated
      Given a selected row has an unsupported, incomplete, or ambiguous condition
      When the evaluator processes that row
      Then an evaluation exception identifies the source row ID and the reason
      And the row is not silently treated as false or reported as passing
      And other supported rows continue to be evaluated
      And an absent condition input is treated according to the configured condition semantics
      And undefined missing-input semantics produce an exception rather than a guessed result

  @IT-34R3
  Rule: Prove the supported conditional-required rows with focused PyTest coverage

    @IT-34R3S1
    Scenario: Verify both branches of each supported condition
      Given the existing XML fixtures and their manifest are available
      And each supported selected conditional-required row is mapped to appropriate test cases
      When parameterized PyTest tests run through the shared evaluator
      Then a true condition with missing required data produces the expected governed finding
      And a true condition with supplied required data produces no finding for that constraint
      And a false condition with missing dependent data produces no finding for that constraint
      And the expected findings are checked by source row ID and affected context
      And existing fixtures are reused when their condition and defect match the test case
      And only missing cases are added as small controlled variations of the source XML
      And unsupported rows and coverage gaps are identified explicitly
      And the existing regression suite remains green
