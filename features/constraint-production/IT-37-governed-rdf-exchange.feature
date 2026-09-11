@constraint-production
@IT-37
Feature: Define governed RDF exchange between constraint-construction stages
  As the governed constraint-production process
  I want construction agents to exchange governed RDF knowledge
  So each stage can consume prior knowledge and produce new knowledge
  without depending on another stage's implementation-specific representation

  Background:
    Given constraint construction is performed as a sequence of governed stages
    And each construction stage is executed by a bounded worker
    And knowledge produced by one stage may be consumed by a later stage
    And PROV-O is used for common execution and provenance relationships

  @IT-37R1
  Rule: A construction-stage result has an explicit governed identity

    @IT-37R1S1
    Scenario: Represent a construction-stage result as governed RDF
      Given a constraint construction stage produces knowledge
      When the stage result is represented for exchange
      Then the result has a governed RDF identity
      And the result identifies the governed constraint
      And the result identifies the construction stage
      And the result records its construction status

    @IT-37R1S2
    Scenario: Reuse the same governed result identity across serializations
      Given a construction-stage result has a governed RDF identity
      When the exchange graph is serialized and read again
      Then the same result identity is preserved
      And a new identity is not minted solely because the serialization changed

  @IT-37R2
  Rule: Exchange knowledge preserves its construction provenance

    @IT-37R2S1
    Scenario: Link a stage result to the activity that generated it
      Given a construction activity produces a stage result
      When the result is represented in the exchange graph
      Then the result is linked to the generating activity with PROV-O
      And the generating activity identifies the bounded worker responsible
      And the activity identifies the governed knowledge it used

    @IT-37R2S2
    Scenario: Preserve construction timing in the exchange graph
      Given a construction activity has started and completed
      When its result is represented in the exchange graph
      Then the activity records its start time
      And the activity records its end time

  @IT-37R3
  Rule: A downstream stage consumes governed RDF rather than an upstream implementation object

    @IT-37R3S1
    Scenario: Consume a prior stage result through RDF identity
      Given an upstream construction stage has produced a governed RDF result
      And a downstream construction stage requires that result
      When the downstream activity records its input
      Then the downstream activity uses the upstream governed RDF result
      And the exchange does not require an implementation-specific object identity

    @IT-37R3S2
    Scenario: Preserve upstream knowledge when a downstream result is produced
      Given a downstream stage consumes an upstream governed RDF result
      When the downstream stage produces its own governed RDF result
      Then the upstream result remains present as governed knowledge
      And the downstream result has its own governed identity
      And the relationship between the two results remains traceable through their activities

  @IT-37R4
  Rule: Construction status and exceptions are exchange knowledge

    @IT-37R4S1
    Scenario: Exchange a successful construction-stage result
      Given a construction stage completes successfully
      When its result is represented for exchange
      Then the result records a successful construction status
      And the result is available for consumption by a downstream stage

    @IT-37R4S2
    Scenario: Exchange an exception instead of invented downstream knowledge
      Given a construction stage cannot produce governed output from the available knowledge
      When the stage records its result
      Then the result records an exception status
      And the exception reason is preserved as governed knowledge
      And the result indicates that review is required
      And no successful stage output is invented

  @IT-37R5
  Rule: Stage-specific knowledge is carried within a common exchange contract

    @IT-37R5S1
    Scenario: Carry normalized constraint knowledge as a stage-specific result
      Given the normalization stage has produced normalized constraint knowledge
      When that knowledge is represented for inter-stage exchange
      Then the exchange graph identifies the result as normalization-stage knowledge
      And the normalized constraint remains independently addressable
      And common exchange metadata does not replace the normalized constraint knowledge

    @IT-37R5S2
    Scenario: Permit later stages to define their own result knowledge
      Given a later construction stage produces knowledge different from normalization
      When its result is represented for inter-stage exchange
      Then the result uses the same common exchange contract
      And the stage-specific knowledge retains its own RDF type and predicates
      And the exchange contract does not require stage-specific knowledge to be encoded as generic text

  @IT-37R6
  Rule: The exchange graph preserves the constraint-construction and validation-execution boundary

    @IT-37R6S1
    Scenario: Keep construction failure distinct from appraisal validation failure
      Given a constraint-construction stage records RED or exception knowledge
      When that knowledge is represented in the exchange graph
      Then it is identified as constraint-construction knowledge
      And it is not identified as an appraisal validation finding
      And it is not identified as a SHACL validation result

    @IT-37R6S2
    Scenario: Exchange finding-definition knowledge without creating a runtime finding
      Given the finding-definition stage produces knowledge describing a future validation finding
      When that knowledge is represented for inter-stage exchange
      Then the result remains constraint-construction knowledge
      And no appraisal validation finding is asserted
      And an actual validation finding requires a separate validation execution
