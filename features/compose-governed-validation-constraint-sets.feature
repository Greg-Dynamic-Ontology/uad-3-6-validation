# Moved from manage-uad-customer-accounts.feature

 @IT-22R1-B
Rule: Apply centrally governed GSE constraints without weakening them

Given GSE constraint sets are centrally governed and versioned

@IT-22R1S2
Scenario: Validate against both GSE rule sets by default
Given a customer account has not selected a target GSE for a validation cycle
When a UAD appraisal report is validated
Then the service applies both Fannie Mae and Freddie Mac rule sets
And the validation result distinguishes shared and GSE-specific findings
And the account default does not alter the centrally governed constraints

@IT-22R1S3
Scenario: Select a target GSE without weakening its constraints
Given a customer account is permitted to select a target GSE for a validation cycle
When the account selects Fannie Mae or Freddie Mac
Then the selected target is recorded on the validation cycle
And the complete centrally governed rule set applicable to that GSE is applied
And the validation result identifies the selected GSE and constraint-set version
And selecting a target does not modify the governed constraint definitions

# End Moved features

