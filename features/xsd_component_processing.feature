Feature: Complete processing of XSD components used by UAD

  As a developer of the UAD validation service
  I want every XSD component used by UAD to be deliberately processed
  So that the Logical Schema Model is complete and unsupported components are visible

  Processing means that an XSD component occurrence is recognized by a tested handler
  and is either represented in the Logical Schema Model or given an explicit,
  documented policy disposition. Merely encountering or counting an occurrence does
  not mean that it has been processed.

  The expected component kinds are documented in
  specs/samples/xsd_extraction/master-list.txt. Runtime discovery and counts come from
  the actual UAD schema closure, not from the extraction report.

  Background:
    Given the official UAD 3.6 XML Schema entry point is configured

  Rule: The complete UAD schema closure is discovered

    @IT-5R1S1
    Scenario: Follow imports through the UAD schema closure
      When the UAD schema is loaded
      Then the entry-point schema is included
      And each recursively imported schema is included
      And each schema document is visited no more than once

    @IT-5R1S2
    Scenario: Inventory every XSD component occurrence
      When the UAD schema closure is inventoried
      Then every element in the XML Schema namespace is recorded by component kind
      And every occurrence records its source schema document
      And the inventory contains the 24 component kinds used by UAD
      And occurrence counts are calculated from the schema documents

  Rule: Schema declarations and documentation preserve their meaning

    @IT-5R2S1
    Scenario: Process schema declarations used by UAD
      When declaration components are processed
      Then element declarations are represented in the Logical Schema Model
      And attribute declarations are represented in the Logical Schema Model
      And attribute group declarations are represented in the Logical Schema Model
      And complex type definitions are represented in the Logical Schema Model
      And simple type definitions are represented in the Logical Schema Model
      And the relationships among those declarations are preserved

    @IT-5R2S2
    Scenario: Preserve schema documentation
      When annotation and documentation components are processed
      Then documentation text is associated with the component it describes
      And the documentation remains available to downstream schema consumers

  Rule: Content models and type derivations preserve their meaning

    @IT-5R3S1
    Scenario: Process model groups used by UAD
      When sequence, choice, and group components are processed
      Then their child declarations and references are represented in the Logical Schema Model
      And their ordering and occurrence constraints are preserved

    @IT-5R3S2
    Scenario: Process type derivations used by UAD
      When restriction, extension, simple content, and union components are processed
      Then base-type relationships are preserved
      And extended or restricted content is preserved
      And union member types are preserved

  Rule: Datatype constraints preserve their meaning

    @@IT-5R4S1
    Scenario: Process datatype facets used by UAD
      When datatype constraint components are processed
      Then enumeration constraints are preserved
      And fractionDigits constraints are preserved
      And maxInclusive constraints are preserved
      And maxLength constraints are preserved
      And minInclusive constraints are preserved
      And minLength constraints are preserved
      And pattern constraints are preserved

  Rule: Schema packaging and wildcards are handled deliberately

    @IT-5R5S1
    Scenario: Process schema imports
      When an import component is processed
      Then its namespace and schema location are preserved
      And the imported schema participates in the schema closure

    @IT-5R5S2
    Scenario: Apply the documented wildcard policy
      When any and anyAttribute components are processed
      Then each occurrence receives the documented wildcard-policy disposition
      And the disposition identifies the governing architecture decision
      And deliberately ignored wildcard occurrences are counted as processed

  Rule: Developer experience reports component-processing coverage

    @IT-5R6S1
    Scenario: Developer sees processing coverage for the UAD schema closure
      Given the active configuration selects the Developer experience
      When the UAD schema has been loaded
      Then the developer sees every XSD component kind found in the schema closure
      And the developer sees the number of occurrences found for each component kind
      And the developer sees the number of occurrences processed for each component kind
      And a component kind with no processed occurrences is marked NP
      And a component kind with fewer processed occurrences than found occurrences is identified as incomplete

    @IT-5R6S2
    Scenario: An unrecognized XSD component remains visible
      Given the schema closure contains an XSD component kind with no processing handler
      When the component-processing coverage is reported
      Then the component kind is included in the report
      And the component kind is marked NP

    @IT-5R6S3
    Scenario: User experience hides schema implementation details
      Given the active configuration selects the User experience
      When the UAD schema has been loaded
      Then the user sees an understandable schema-loading status
      And the user does not receive the component-processing coverage report

  Rule: Complete processing is reconcilable and deterministic

    @IT-5R7S1
    Scenario: Every discovered occurrence has a processing disposition
      When processing of the official UAD schema closure completes
      Then every discovered XSD component occurrence has exactly one processing disposition
      And the found and processed counts reconcile for every component kind
      And no UAD component kind is marked NP
      And no UAD component kind is identified as incomplete

    @IT-5R7S2
    Scenario: Combined and individual UAD schemas produce equivalent models
      When the Combined and Individual UAD schema distributions are loaded
      Then they produce equivalent Logical Schema Models
      And their component-processing coverage reconciles to their respective schema closures

    @IT-5R7S3
    Scenario: Reprocess the same UAD schema closure
      When the same UAD schema closure is processed more than once
      Then each run produces an equivalent Logical Schema Model
      And each run produces the same component-processing coverage
