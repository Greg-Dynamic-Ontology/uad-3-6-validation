@IT-2
Feature: Submit appraisal XML and present RDF validation results
  A client submits an appraisal as application/xml.
  The validation service returns its results as RDF serialized in Turtle.
  The UI builds its HTML presentation from that same RDF knowledge.

  Background:
    Given the governed validation rule inventory is available
    And the selected validation rules are defined

    @IT-2R1
    Rule: The validation API accepts an XML document directly

    @IT-2R1S1 @Submit_an_appraisal_XML_document
    Scenario: Submit an appraisal XML document
      Given an appraisal XML document
      When a client posts the document to "/validate/uad36" with Content-Type "application/xml" and Accept "text/turtle"
      Then the service reads the request body as the appraisal XML document
      And the service evaluates the selected validation rules
      And no JSON wrapper is required

    @IT-2R1S2 @Reject_an_unsupported_request_representation
    Scenario: Reject an unsupported request representation
      Given a request whose Content-Type is not supported
      When the client posts the request to "/validate/uad36" with Accept "text/turtle"
      Then the service responds with HTTP status 415
      And the response has Content-Type "text/turtle"
      And the response graph explains the unsupported request representation
      And the service does not evaluate the appraisal

  @IT-2R2
  Rule: Validation results are returned as RDF knowledge in Turtle

    @IT-2R2S1 @Return_findings_for_a_processed_appraisal
    Scenario: Return findings for a processed appraisal
      Given an appraisal XML document that violates a selected rule
      When the client submits the document for validation
      Then the service responds with HTTP status 200
      And the response has Content-Type "text/turtle"
      And the response body parses as Turtle
      And the result graph identifies the validation run
      And the result graph identifies the submitted source document
      And the result graph identifies the evaluated rule selection
      And the result graph distinguishes processing completion from validation outcome
      And each finding is linked to the validation run
      And each finding identifies its source row, Rule ID, and severity
      And each finding identifies its affected XML context
      And each finding describes the violation
      And the result uses governed RDF vocabulary and identity policies

    @IT-2R2S2 @Return_an_explicit_result_when_no_violations_are_found
    Scenario: Return an explicit result when no violations are found
      Given an appraisal XML document that satisfies all selected rules
      When the client submits the document for validation
      Then the service responds with HTTP status 200
      And the response has Content-Type "text/turtle"
      And the response body parses as Turtle
      And the result graph identifies the validation run and evaluated rule selection
      And the result graph explicitly records successful processing with no findings
      And the result does not claim coverage of rules outside that selection


    @IT-2R2S3 @Report_malformed_XML_as_RDF
    Scenario: Report malformed XML as RDF
      Given a request body that is not well-formed XML
      When the client submits it with Content-Type "application/xml" and Accept "text/turtle"
      Then the service responds with HTTP status 400
      And the response has Content-Type "text/turtle"
      And the response body parses as Turtle
      And the result graph identifies the processing failure
      And the result graph explains why the XML could not be read
      And the result does not claim that rule evaluation completed successfully

  @IT-2R3
  Rule: Saved fixture expectations can be verified through the API

    @IT-2R3S1 @Verify_a_fixture_through_XML_submission_and_Turtle_results
    Scenario: Verify a fixture through XML submission and Turtle results
      Given a saved XML fixture described by "manifest.ttl"
      And the manifest identifies the selected source rule and expected findings
      When a test client submits the fixture as "application/xml" and requests "text/turtle"
      Then the client parses the response as an RDF graph
      And the findings for the selected source rule match the manifest
      And the comparison checks finding count, severity, violation kind, and XML context
      And unrelated findings cannot substitute for an expected finding
      And unrelated findings remain available in the returned graph
      And the test does not generate or modify the saved XML fixture

  @IT-2R4
  Rule: The UI derives its HTML presentation from the returned RDF

    @IT-2R4S1 @Present_validation_findings_from_Turtle
    Scenario: Present validation findings from Turtle
      Given the user selects an appraisal XML file in the UI
      When the user requests validation
      Then the UI submits the file contents as "application/xml"
      And the UI requests a "text/turtle" response
      And the UI parses the returned Turtle into an RDF graph
      And the UI builds its HTML results from that graph
      And the presentation shows the validation run and validation outcome
      And the presentation shows each finding's Rule ID, severity, description, and XML context
      And the UI does not require a parallel JSON validation response
      And the UI does not independently re-evaluate the validation rules

    @IT-2R4S2 @Present_an_explicit_result_with_no_findings
    Scenario: Present an explicit result with no findings
      Given the returned result graph records successful processing with no findings
      When the UI builds the HTML results
      Then the presentation states that no violations were found for the evaluated rule selection
      And the presentation does not imply that unevaluated rules passed

    @IT-2R4S3 @Present_a_processing_failure_from_Turtle
    Scenario: Present a processing failure from Turtle
      Given the service returns a non-success HTTP status with a Turtle result graph
      When the UI receives the response
      Then the UI parses the returned Turtle
      And the UI presents the processing failure described by the graph
      And the UI does not present the appraisal as having passed validation

    @IT-2R4S4 @Report_an_unreadable_Turtle_response
    Scenario: Report an unreadable Turtle response
      Given the response body cannot be parsed as Turtle
      When the UI attempts to read the validation results
      Then the UI reports that the validation results could not be read
      And the UI does not interpret the unreadable response as an absence of findings