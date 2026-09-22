Feature: Validate reports using governed constraints
  As a validation service
  I want each governed constraint to be evaluated in its applicable context
  So that validation findings are produced consistently from governed constraint knowledge

  Background:
    Given governed constraints have been normalized from authoritative source evidence
    And each governed constraint retains its identity, applicability, violation condition, severity, and provenance

  # IT-32 — Execute governed constraints as repeatable validation behavior
  @IT-32R1
  Rule: Apply a governed constraint to its applicable context

    @IT-32R1S1
    Scenario: Evaluate a governed constraint
      Given a governed constraint identifies the context in which it applies
      And the governed constraint identifies the condition that constitutes a violation
      And the governed constraint identifies the finding identity and severity to report
      When a report is validated against the governed constraint
      Then the constraint is evaluated only in its applicable context
      And a satisfied violation condition produces the governed finding
      And the finding reports the governed severity
      And the finding remains traceable to the governed constraint and its source evidence
      And an unsatisfied violation condition produces no finding for that constraint
