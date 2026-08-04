Feature: Upload a UAD XML appraisal

  As a ServiceLink user
  I want to upload a UAD 3.6 appraisal XML document
  So that the document can be evaluated by the validation service

  Scenario: Home page offers appraisal upload
    Given the UAD 3.6 Validation application is running
    When I open the home page
    Then I see a control for selecting an XML file
    And I see a button labeled "Evaluate Appraisal"

  Scenario: User uploads an XML document
    Given I have selected a UAD XML appraisal document
    When I submit the document
    Then the application accepts the upload
    And the application displays the uploaded filename
    And the application reports that the document is ready for evaluation

  Scenario: User attempts to upload a non-XML document
    Given I have selected a document that is not XML
    When I submit the document
    Then the application rejects the upload
    And the application explains that a UAD XML document is required