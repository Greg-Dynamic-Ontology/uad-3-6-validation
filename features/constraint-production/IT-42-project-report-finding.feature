Feature: 7 Project SHACL validation results into governed report findings
  As the governed validation process
  I want a report-finding agent to project SHACL validation results into governed validation findings
  So that validation output reports governed meaning, severity, identity, and provenance rather than exposing SHACL mechanics as the domain result

  Background:
    Given a normalized governed constraint is available
    And the governed constraint has an executable SHACL representation
    And the SHACL representation identifies the governed constraint it implements
    And SHACL validation has produced a validation report
    And the governed constraint knowledge is available
    And the report-finding agent has an explicit input, output, and error contract

  # IT-42R1 — Project a SHACL violation into a governed validation finding

  @IT-42R1
  Rule: Produce a governed validation finding for each governed SHACL violation

    @IT-42R1S1
    Scenario: Project one SHACL validation result into one governed validation finding
      Given the SHACL validation report contains a validation result
      And the validation result was produced by a shape that implements one governed constraint
      When the report-finding agent executes
      Then one governed validation finding is produced for that validation result
      And the finding identifies the governed constraint
      And the finding identifies the governed source constraint
      And the finding identifies the governed source rule
      And the finding reports the governed severity
      And the finding reports the governed violation kind
      And the finding identifies the SHACL focus node
      And the finding remains traceable to the SHACL validation result
      And the finding remains traceable to the governed source knowledge
      And the finding is available to the validation reporting process

  # IT-42R2 — Enrich validation mechanics with governed meaning

  @IT-42R2
  Rule: Governed finding meaning comes from governed constraint knowledge rather than SHACL mechanics

    @IT-42R2S1
    Scenario: Combine a SHACL validation result with its governed constraint knowledge
      Given a SHACL validation result identifies the shape that produced it
      And that shape identifies the governed constraint it implements
      When the report-finding agent projects the result
      Then validation mechanics are obtained from the SHACL validation result
      And governed identity is obtained from the governed constraint knowledge
      And governed severity is obtained from the governed constraint knowledge
      And governed violation meaning is obtained from the governed constraint knowledge
      And governed source traceability is obtained from the governed constraint knowledge
      And SHACL-specific identifiers do not replace governed constraint identities

  # IT-42R3 — Produce no governed finding without a governed violation

  @IT-42R3
  Rule: Do not invent a report finding when SHACL validation produced no governed violation

    @IT-42R3S1
    Scenario: Produce no finding for a conforming validation report
      Given the SHACL validation report contains no validation result for a governed constraint
      When the report-finding agent executes
      Then no governed validation finding is produced for that constraint
      And the absence of a SHACL violation is not converted into a finding

  # IT-42R4 — Reject validation results that cannot be governed

  @IT-42R4
  Rule: Do not invent governed meaning for an unresolvable SHACL validation result

    @IT-42R4S1
    Scenario: Reject a SHACL validation result that cannot be traced to a governed constraint
      Given the SHACL validation report contains a validation result
      And the shape that produced the result cannot be resolved to a governed constraint
      When the report-finding agent executes
      Then no governed validation finding is produced for that validation result
      And an exception is produced
      And the exception identifies the report-finding stage
      And the exception identifies the SHACL validation result
      And the agent does not invent a governed constraint identity
      And the exception is eligible to be written to the Batch Results Graph

    @IT-42R4S2
    Scenario: Reject a governed constraint whose required finding knowledge is incomplete
      Given a SHACL validation result can be traced to a governed constraint
      And governed knowledge required by the finding contract is missing
      When the report-finding agent executes
      Then no incomplete governed validation finding is produced
      And an exception is produced
      And the exception identifies the governed constraint
      And the exception identifies the missing governed knowledge
      And the agent does not infer or invent a replacement value
      And the constraint is routed for review

  # IT-42R5 — Satisfy the report-finding agent contract

  @IT-42R5
  Rule: The report-finding agent behaves as a bounded worker

    @IT-42R5S1
    Scenario: Return only contracted output or a contracted exception
      Given the report-finding agent receives a SHACL validation report and governed constraint knowledge
      When the report-finding agent completes its work
      Then it returns governed validation findings or report-finding exceptions
      And it does not change normalized governed constraint meaning
      And it does not change the governed Logical Schema binding
      And it does not change the governed applicable context
      And it does not change the governed validation behavior
      And it does not change the governed Instance RDF binding
      And it does not change the executable SHACL representation
