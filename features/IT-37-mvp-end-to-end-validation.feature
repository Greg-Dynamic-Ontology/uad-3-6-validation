Feature: IT-37-mvp-end-to-end-validation.feature
Run the selected constraint set against an uploaded UAD file and produce the customer-facing findings/report.

  Background:
    Given the existing customer upload and validation path is available
    And the selected MVP constraint set and its supported coverage are identified
    And the reusable evaluators from IT-33 through IT-36 are available

  # IT-37 — Connect the working evaluators to the existing customer path.
  # Reuse the existing upload, validation-cycle, and reporting infrastructure.
  # Prove the selected MVP coverage; do not require all source constraints or deferred OTDD work.
  # Automated billing and new account workflows are outside this iteration.

  @IT-37R1
  Rule: Run schema and supported business-rule validation for the uploaded report

    @IT-37R1S1
    Scenario: Validate a readable uploaded UAD XML file
      Given a customer uploads a well-formed UAD XML file through the existing validation path
      When validation runs
      Then the uploaded file is checked against the governed UAD schema
      And the supported selected constraints are evaluated using the shared evaluators
      And schema results and business-rule findings remain distinguishable
      And schema errors do not suppress business-rule checks that can still be evaluated reliably
      And checks that cannot run are identified with their reasons
      And the result identifies the uploaded report, validation run, and constraint-set version used
      And validation does not alter the uploaded XML

    @IT-37R1S2
    Scenario: Return a clear failure when validation cannot proceed
      Given an upload cannot be parsed as XML or validation encounters an execution failure
      When the validation request is processed
      Then the customer receives a clear explanation of the failure and any action they can take
      And the result is not presented as a successful validation
      And any available partial results are clearly identified as incomplete
      And unevaluated checks are not reported as passing
      And the customer can submit a corrected file or retry through the existing path

  @IT-37R2
  Rule: Present actionable findings and an honest coverage summary

    @IT-37R2S1
    Scenario: Review and download validation results
      Given a validation run has produced results
      When the customer opens the result
      Then the result shows whether validation completed and whether findings were detected
      And business-rule findings identify the source row ID, source rule ID, severity, and affected element or context
      And each finding explains the problem and the expected data or restriction
      And the result distinguishes evaluated checks from deferred or failed checks
      And unresolved evaluation exceptions make the result visibly incomplete
      And no-findings results state that no issues were found within the evaluated coverage
      And the result does not claim compliance with constraints outside the selected MVP coverage
      And the customer can download a report containing the same findings, coverage, and run identity
      And findings appear in a stable order without duplicate entries for the same constraint and occurrence

  @IT-37R3
  Rule: Validate a corrected upload as a new run

    @IT-37R3S1
    Scenario: Confirm that correcting a reported defect removes its finding
      Given a customer has a validation result identifying a defect
      And the customer corrects that defect in the XML
      When the corrected file is uploaded and validated through the existing path
      Then a new validation result is associated with the corrected upload
      And the corrected defect no longer produces its previous finding
      And any remaining defects continue to produce their findings
      And findings from the earlier run are not carried into the new result
      And the new downloadable report corresponds to the corrected upload and new run

  @IT-37R4
  Rule: Prove the MVP through the actual upload-to-report path

    @IT-37R4S1
    Scenario: Verify the integrated customer workflow
      Given a positive-control XML file conforming to the selected checks is available
      And existing negative fixtures cover supported constraints from IT-33 through IT-36
      And only missing test cases have been added as controlled variations of the source XML
      When integration tests submit the files through the upload endpoint used by the customer interface
      Then the positive control completes without unexpected findings
      And each negative case produces the expected source row ID and affected context in the result and downloadable report
      And malformed XML and evaluation failures produce clear unsuccessful or incomplete results
      And a corrected resubmission removes the expected finding in a new run
      And the existing regression suite remains green
      And a browser smoke check confirms upload, result display, report download, and corrected resubmission work together
