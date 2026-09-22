  Feature:  Required Data Validation
    Load the inventory, locate the governed element, determine whether required data is present, and produce a finding.
    This one generic mechanism should handle many of those 53 fixtures.

    As the UAD 3.6 validation process
    I want selected required-data constraints to use one reusable evaluator
    So that the MVP detects missing required data with governed, actionable findings

  Background:
    Given the selected MVP constraint inventory is available
    And the spreadsheet row ID is the authoritative source constraint identity
    And column B of the governed spreadsheet identifies the Primary Data Element
    And the governed UAD 3.6 schema vocabulary and XML namespace bindings are available
    And the existing negative XML fixtures and their manifest are available in "data/uad36-required-data-tests"
    And the corresponding complete source XML is available as the positive control

  # IT-33 — Implement the reusable required-data capability for the MVP fast path
  # Reuse the existing fixtures; do not create one scenario or Python validator per spreadsheet row.
  # The manifest maps fixtures to constraints; it does not establish governed requirement meaning.
  # The 53 fixtures are the candidate corpus, not an asserted count of unconditional required rules.
  # Conditional requirements belong to IT-34; value/domain checks to IT-35;
  # numeric/format checks to IT-36; customer end-to-end validation to IT-37.
  # IT-N1 through IT-N3 retain the deferred constraint-construction work.
  # New RDF/SHACL construction stages are not prerequisites for this iteration.

  @IT-33R1
  Rule: Load the selected required-data constraints without changing governed identity or meaning

    @IT-33R1S1
    Scenario: Select inventory rows supported by the required-data evaluator
      Given the inventory contains selected constraints with governed requirement knowledge
      When the required-data constraint set is loaded
      Then each selected unconditional required-data constraint is configured for the same reusable evaluator
      And each configuration preserves the spreadsheet row ID as text including leading zeros
      And each configuration preserves the source rule ID and Primary Data Element
      And each configuration identifies the governed XML context and applicable property scope
      And each configuration supplies the governed severity, violation meaning, and source provenance
      And conditional-required and other unsupported behaviors are identified as deferred
      And deferred constraints are not reported as evaluated or passing
      And the executable subset is derived from the inventory rather than a fixed fixture count

    @IT-33R1S2
    Scenario: Identify a constraint that cannot be evaluated reliably
      Given a selected required-data constraint has missing, conflicting, or unresolved configuration
      When the required-data constraint set is loaded
      Then an exception identifies the spreadsheet row ID when available and the configuration problem
      And the affected constraint is not evaluated or reported as passing
      And no governed identity, context, severity, or requirement meaning is invented
      And other valid selected constraints remain eligible for evaluation

  @IT-33R2
  Rule: Locate required data within its governed XML context

    @IT-33R2S1
    Scenario: Evaluate the subject property's physical address in its governed context
      Given constraint "0100.0007" identifies source rule "UAD1001" and Primary Data Element "AddressLineText"
      And its governed context is the subject property's physical address
      And the subject property's required AddressLineText is absent
      And another property's address contains AddressLineText
      When the required-data evaluator processes the XML
      Then the other property's AddressLineText does not satisfy constraint "0100.0007"
      And the missing data is associated with the subject property's address context
      And element matching uses namespace-qualified identity rather than local name alone

    @IT-33R2S2
    Scenario: Check each applicable occurrence independently
      Given a selected required-data constraint applies to multiple context occurrences
      And one applicable occurrence has the required data
      And another applicable occurrence lacks the required data
      When the required-data evaluator processes the XML
      Then the populated occurrence produces no missing-data finding for that constraint
      And the deficient occurrence produces one missing-data finding for that constraint
      And the finding identifies the deficient occurrence unambiguously

    @IT-33R2S3
    Scenario: Account for an absent required context
      Given a selected unconditional required-data constraint requires a governed context to exist
      And that context is absent from the XML
      When the required-data evaluator processes the XML
      Then the absence is reported against the expected governed context and nearest existing ancestor
      And an empty context selection is not treated as successful validation
      And a context whose applicability requires an unresolved condition is deferred to conditional-required validation

  @IT-33R3
  Rule: Apply the same required-data behavior to every supported inventory row

    @IT-33R3S1
    Scenario: Detect an absent required element
      Given a selected required-data constraint has an applicable governed context
      And its required element is absent from that context
      When the reusable required-data evaluator evaluates the constraint
      Then exactly one missing-data finding is produced for that constraint and deficient context occurrence
      And the behavior is selected by inventory configuration rather than row-specific Python code

    @IT-33R3S2
    Scenario: Detect a required scalar element without a supplied value
      Given a selected required-data constraint requires a supplied scalar value
      And the applicable element is empty, contains only whitespace, or is explicitly nil
      When the reusable required-data evaluator evaluates the constraint
      Then exactly one missing-data finding is produced for that constraint and deficient context occurrence

    @IT-33R3S3
    Scenario: Accept a supplied required value
      Given a selected required-data constraint has an applicable governed context
      And its required element contains a nonblank value and is not nil
      When the reusable required-data evaluator evaluates the constraint
      Then no missing-data finding is produced for that constraint and context occurrence
      And a supplied zero or false value is not treated as missing
      And presence alone does not assert conformance with value, domain, numeric, or format constraints

  @IT-33R4
  Rule: Return deterministic findings traceable to governed requirements

    @IT-33R4S1
    Scenario: Produce an actionable finding for missing required data
      Given evaluation detects missing required data for a selected constraint
      When the result is projected into a governed validation finding
      Then the finding identifies the authoritative spreadsheet row ID and source rule ID
      And the finding identifies the Primary Data Element and affected property scope
      And the finding identifies the actual deficient context or expected path when the context is absent
      And the finding reports the governed severity and missing-required-data violation kind
      And the finding explains which required data must be supplied
      And the finding remains traceable to the governed source requirement
      And a fixture filename or implementation identifier does not replace governed identity

    @IT-33R4S2
    Scenario: Repeat evaluation with unchanged inputs
      Given the same XML and the same selected constraint configuration
      When required-data validation is executed repeatedly
      Then the governed finding content and finding order are identical
      And findings have a stable order by spreadsheet row ID and affected context occurrence
      And no duplicate finding is emitted for the same constraint and deficient context occurrence
      And evaluation does not modify the source XML, inventory, or fixtures
      And evaluation exceptions remain distinguishable from business-rule findings

  @IT-33R5
  Rule: Prove the reusable capability with the existing fixture corpus and PyTest

    @IT-33R5S1
    Scenario: Establish executable expectations before implementing required-data behavior
      Given each supported selected constraint is mapped by row ID to its existing manifest entries
      And expected findings are derived from governed requirements and the manifest's recorded defect
      When parameterized PyTest tests are run before the required behavior is implemented
      Then the tests establish a RED state for the missing required-data behavior
      And failures caused only by missing files or broken test setup do not establish that RED state
      And the tests exercise the supported rows without separate feature scenarios or validators for each row

    @IT-33R5S2
    Scenario: Prove the positive control and each supported negative fixture
      Given the reusable required-data evaluator has been implemented
      When parameterized PyTest tests evaluate the complete source XML and each supported negative fixture
      Then the positive control produces no missing-data findings for the tested constraints
      And each negative fixture produces the expected finding for its manifest row ID and affected context
      And each expected finding has the governed rule ID, element, severity, and violation meaning
      And no unexpected missing-data findings are produced for the tested constraint set
      And schema-validation results remain separate from required-data evaluation results
      And schema conformance alone does not establish required-data conformance
      And the existing negative fixtures are reused without regeneration

    @IT-33R5S3
    Scenario: Complete the iteration with explicit coverage and a green regression suite
      Given all supported required-data fixture tests pass
      And context isolation, repeated occurrences, absent required contexts, blank values, and deterministic findings are verified
      When the full existing regression suite is executed
      Then the regression suite remains green
      And the verification result identifies evaluated row IDs and their fixture coverage
      And deferred constraints and unresolved exceptions are listed with reasons
      And missing fixture coverage is identified rather than counted as a passing test
      And unresolved exceptions or missing coverage for the agreed supported subset prevent iteration completion
      And completion does not claim support for all 53 fixtures or all 729 source constraints
