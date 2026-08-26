# Moved from manage-uad-customer-accounts.feature
Feature: Compose governed validation constraint sets
  As a validation service
  I want to compose all applicable governed constraint sets
  So that every report is evaluated consistently without weakening authority requirements

  Background:
    Given governed constraint sets from GSEs and other authorities are centrally registered, versioned, and effective-dated

  @IT-22R1-B
  Rule: Apply centrally governed GSE constraints without weakening them

    @IT-22R1S2
    Scenario: Validate against both GSE rule sets by default
      Given a customer account has not selected a target GSE for a validation cycle
      When a UAD appraisal report is validated
      Then the service applies every shared GSE constraint once
      And the service applies every Fannie Mae-only constraint
      And the service applies every Freddie Mac-only constraint
      And the validation result distinguishes shared and GSE-specific findings
      And the account default does not alter the centrally governed constraints

    @IT-22R1S3
    Scenario Outline: Select a target GSE without weakening its constraints
      Given a customer account is permitted to select a target GSE for a validation cycle
      When the account selects <target GSE>
      Then the selected target is recorded on the validation cycle
      And every shared GSE constraint is applied
      And every <GSE-specific classification> constraint is applied
      And constraints classified only for the other GSE are not applied
      And the validation result identifies the selected GSE and constraint-set version
      And selecting a target does not modify the governed constraint definitions

      Examples:
        | target GSE  | GSE-specific classification |
        | Fannie Mae  | Fannie Mae-only             |
        | Freddie Mac | Freddie Mac-only             |

# End moved features

  @IT-24R1
  Rule: Compose every active and applicable governed constraint set

    @IT-24R1S1
    Scenario: Classify every GSE constraint exactly once
      Given a governed GSE constraint is registered
      When its GSE applicability is classified
      Then it is classified as exactly one of Fannie Mae-only, Freddie Mac-only, or shared
      And registration is rejected if none or more than one of those classifications applies

    @IT-24R1S2
    Scenario Outline: Compose optional governed overlays with the selected GSE constraints
      Given a validation cycle has selected its applicable GSE constraints
      And <overlay selection> governed lender, AMC, or other authority overlays are applicable
      When the effective constraint set is composed
      Then it is the union of every active and applicable selected GSE constraint and governed overlay

      Examples:
        | overlay selection |
        | no                |
        | one               |
        | multiple          |

    @IT-24R1S3
    Scenario Outline: Exclude a governed set that is not active and applicable
      Given a governed constraint set is <set condition>
      When the effective constraint set is composed
      Then that constraint set is excluded

      Examples:
        | set condition                      |
        | inactive                           |
        | expired                            |
        | not yet effective                  |
        | inapplicable to the validation cycle |

    @IT-24R1S4
    Scenario Outline: Prevent an overlay from weakening a GSE constraint
      Given an active governed overlay conflicts with an applicable GSE constraint
      When the overlay attempts to <weakening action> the GSE constraint
      Then the effective constraint set is rejected
      And the GSE constraint remains unchanged

      Examples:
        | weakening action |
        | disable          |
        | downgrade        |

    @IT-24R1S5
    Scenario: Reject contradictory active constraints
      Given two active and applicable governed constraints contradict one another
      When the effective constraint set is composed
      Then composition is rejected
      And the service does not silently choose one authority over the other

    @IT-24R1S6
    Scenario: Deduplicate constraints only by canonical identity
      Given active and applicable governed sets contain constraints with the same canonical constraint identity
      When the effective constraint set is composed
      Then those occurrences are applied as one constraint
      And constraints with different canonical identities remain distinct even when their requirements appear equivalent

    @IT-24R1S7
    Scenario: Record the provenance of every applied constraint set
      Given an effective constraint set has been composed
      When its composition is recorded for the validation cycle
      Then every applied set records its governing authority, set ID, and version
