Feature: Prevent governed constraints from weakening applicable requirements
  As a constraint governance service
  I want every supplemental constraint classified and compared with the requirements it affects
  So that investor, government-program, AMC, lender, and other constraints may strengthen applicable requirements but never weaken them

  Background:
    Given governed constraint sets and their releases are represented in the shared RDF dataset
    And applicable constraint-set relationships identify requirements that must not be weakened

  @IT-32R1
  Rule: Classify how every supplemental constraint affects governed requirements

    @IT-32R1S1
    Scenario: Classify an independent supplemental constraint as additive
      Given a supplemental constraint introduces a requirement independent of every applicable protected constraint
      When the supplemental constraint is registered
      Then it is classified as additive
      And it is applied in conjunction with every applicable protected constraint
      And it does not replace, disable, or modify another constraint

    @IT-32R1S2
    Scenario: Classify a supplemental constraint as a refinement
      Given a supplemental constraint changes the accepted values of an applicable protected requirement
      When the supplemental constraint is registered
      Then it identifies the protected constraint by governed RDF IRI
      And it is classified as a proposed refinement
      And it cannot become active until its strength relationship is determined

    @IT-32R1S3
    Scenario: Refuse to activate an unclassified supplemental constraint
      Given a supplemental constraint has not been classified as additive or as a refinement of identified constraints
      When activation is requested
      Then activation is rejected
      And the missing relationship classification is reported for governance review

    @IT-32R1S4
    Scenario: Determine protection from governed relationships rather than labels
      Given two applicable constraint-set releases have a governed must-not-weaken relationship
      When their constraints are compared
      Then the protected and supplemental roles are determined from that relationship
      And no precedence is inferred only from a type, name, filename, directory, or loading order

  @IT-32R2
  Rule: Normalize constraint semantics before comparing their strength

    @IT-32R2S1
    Scenario: Represent a comparable constraint with typed semantics
      Given a governed constraint can be expressed by a supported semantic family
      When its comparison representation is created
      Then the representation identifies its target, applicability, operator, operand, datatype, and unit when applicable
      And it identifies the constraint family used to compare its accepted values
      And it retains the exact release-specific definition and source provenance

    @IT-32R2S2
    Scenario: Normalize comparable values without changing their meaning
      Given two constraints express comparable values using different equivalent units or lexical forms
      When their strength is compared
      Then their operands are normalized to the governed datatype and unit
      And the original source values remain available as provenance

    @IT-32R2S3
    Scenario: Refuse to compare constraint prose as if it were typed semantics
      Given a constraint has source prose but no deterministic supported semantic representation
      When its strength relationship is requested
      Then the service does not infer executable meaning from the prose
      And the comparison is classified as requiring governance review

  @IT-32R3
  Rule: Compare numeric boundaries according to their operators

    @IT-32R3S1
    Scenario Outline: Compare a proposed minimum with a protected minimum
      Given an applicable protected constraint requires a minimum value of <protected minimum>
      And a proposed refinement requires a minimum value of <proposed minimum>
      When the proposed refinement is compared with the protected constraint
      Then the strength relationship is <relationship>

      Examples:
        | protected minimum | proposed minimum | relationship |
        | 85%               | 87%              | strengthens  |
        | 85%               | 85%              | equivalent   |
        | 85%               | 84%              | weakens      |

    @IT-32R3S2
    Scenario Outline: Compare a proposed maximum with a protected maximum
      Given an applicable protected constraint permits a maximum value of <protected maximum>
      And a proposed refinement permits a maximum value of <proposed maximum>
      When the proposed refinement is compared with the protected constraint
      Then the strength relationship is <relationship>

      Examples:
        | protected maximum | proposed maximum | relationship |
        | 85%               | 84%              | strengthens  |
        | 85%               | 85%              | equivalent   |
        | 85%               | 87%              | weakens      |

    @IT-32R3S3
    Scenario: Refuse to compare incompatible numeric quantities
      Given two numeric constraints have incompatible datatypes, units, targets, or applicability
      When their strength is compared
      Then neither numerical value is treated as stronger merely because it is greater or smaller
      And the comparison is classified as incomparable or requiring governance review

  @IT-32R4
  Rule: Compare value sets, presence, and cardinality by accepted-value inclusion

    @IT-32R4S1
    Scenario Outline: Compare permitted value sets
      Given an applicable protected constraint permits <protected values>
      And a proposed refinement permits <proposed values>
      When the proposed refinement is compared with the protected constraint
      Then the strength relationship is <relationship>

      Examples:
        | protected values | proposed values | relationship |
        | A, B, C          | A, B            | strengthens  |
        | A, B, C          | A, B, C         | equivalent   |
        | A, B, C          | A, B, C, D      | weakens      |

    @IT-32R4S2
    Scenario Outline: Compare occurrence constraints
      Given an applicable protected constraint has <protected boundary>
      And a proposed refinement has <proposed boundary>
      When the proposed refinement is compared with the protected constraint
      Then the strength relationship is <relationship>

      Examples:
        | protected boundary | proposed boundary | relationship |
        | minCount 1         | minCount 2        | strengthens  |
        | minCount 1         | minCount 0        | weakens      |
        | maxCount 3         | maxCount 2        | strengthens  |
        | maxCount 3         | maxCount 4        | weakens      |

    @IT-32R4S3
    Scenario: Prevent a required value from becoming optional
      Given an applicable protected constraint requires a value
      And a proposed refinement makes that value optional
      When the proposed refinement is compared with the protected constraint
      Then the proposed refinement is classified as weakening

  @IT-32R5
  Rule: Include applicability and enforcement in the strength relationship

    @IT-32R5S1
    Scenario: Treat narrower applicability as a weakening refinement
      Given an applicable protected constraint enforces a requirement under a governed condition
      And a proposed refinement enforces the requirement under a narrower condition
      When the proposed refinement is compared with the protected constraint
      Then the proposed refinement is classified as weakening
      And it cannot exempt cases covered by the protected condition

    @IT-32R5S2
    Scenario: Allow a refinement to cover additional applicable cases
      Given an applicable protected constraint enforces a requirement under a governed condition
      And a proposed refinement enforces an equivalent or stronger requirement for every protected case and additional cases
      When the proposed refinement is compared with the protected constraint
      Then the proposed refinement is classified as strengthening

    @IT-32R5S3
    Scenario Outline: Compare enforcement severity
      Given an applicable protected constraint has <protected severity>
      And a proposed refinement has <proposed severity>
      When the governed severity ordering is compared
      Then the enforcement relationship is <relationship>

      Examples:
        | protected severity | proposed severity | relationship |
        | warning            | fatal             | strengthens  |
        | fatal              | fatal             | equivalent   |
        | fatal              | warning           | weakens      |

  @IT-32R6
  Rule: Preserve protected constraints while composing supplemental constraints

    @IT-32R6S1
    Scenario: Activate a strengthening refinement
      Given a proposed refinement has been proven to strengthen an applicable protected constraint
      When the effective constraints are composed
      Then the protected constraint remains unchanged and traceable
      And the strengthening refinement is also applied
      And the effective accepted values are a subset of those accepted by the protected constraint

    @IT-32R6S2
    Scenario: Reject a weakening refinement instead of masking it
      Given a proposed refinement has been determined to weaken an applicable protected constraint
      When activation or composition is requested
      Then the supplemental constraint-set release is rejected
      And the weakening refinement is not silently ignored as redundant
      And the protected constraint remains unchanged

    @IT-32R6S3
    Scenario: Reject contradictory active constraints
      Given supplemental constraints are individually additive or strengthening
      And their combined accepted-value set is empty for an applicable case
      When the effective constraints are composed
      Then composition is rejected as contradictory
      And the service does not silently choose one constraint over another

    @IT-32R6S4
    Scenario: Apply multiple compatible strengthening constraints
      Given multiple applicable supplemental constraints strengthen or add to protected requirements
      And their combined accepted-value set is not empty
      When the effective constraints are composed
      Then every compatible constraint is applied conjunctively
      And no applicable protected constraint is removed or weakened

  @IT-32R7
  Rule: Require governance for an unprovable strength relationship

    @IT-32R7S1
    Scenario: Keep an incomparable refinement inactive
      Given a proposed refinement uses semantics for which no governed comparator can prove accepted-value inclusion
      When its strength relationship is evaluated
      Then the relationship is classified as incomparable or requiring governance review
      And the proposed refinement remains inactive

    @IT-32R7S2
    Scenario: Activate a manually governed strengthening decision
      Given an authorized governance review has determined that an otherwise unprovable refinement strengthens a protected constraint
      And the decision identifies its evidence, reviewer, scope, and applicable releases
      When the decision is approved
      Then the refinement may become active only within the approved scope
      And the automated comparison result remains distinguishable from the governed decision

    @IT-32R7S3
    Scenario: Do not reuse a governed decision for another release silently
      Given a governed strengthening decision applies to specific constraint definitions and releases
      When either definition or release changes
      Then the prior decision does not automatically approve the changed refinement
      And the strength relationship must be evaluated again

  @IT-32R8
  Rule: Preserve an auditable strengthening decision for every refinement

    @IT-32R8S1
    Scenario: Record an automated strength comparison
      Given a supported comparator has evaluated a proposed refinement
      When the comparison is recorded
      Then the record identifies the protected and supplemental constraint definitions
      And it identifies their constraint-set releases and semantic family
      And it records normalized operands, applicability, severity, result, and comparator version

    @IT-32R8S2
    Scenario: Explain why a supplemental constraint was rejected
      Given activation or composition rejects a weakening, contradictory, or incomparable constraint
      When its governance record is requested
      Then the record identifies the exact failed comparison or contradiction
      And it identifies the contributing definitions and authoritative provenance
      And it explains the disposition without rewriting any source constraint
