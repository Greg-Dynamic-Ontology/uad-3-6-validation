Feature: Manage governed constraints as one RDF dataset
  As a validation service operator
  I want governed constraint artifacts managed as globally connected RDF resources
  So that one service build can validate with different conforming constraint data without changing its code

  Background:
    Given authoritative constraint source evidence is centrally registered and versioned
    And governed domain models and their source-to-RDF mappings are centrally registered and versioned

  @IT-31R1
  Rule: Give every governed constraint artifact an explicit RDF identity

    @IT-31R1S1
    Scenario: Add a constraint-set release to the shared RDF dataset
      Given a governed constraint-set release has a constraint domain, authority, set identity, authority-issued release identifier, and source digest
      When the release is represented internally
      Then the release has a stable RDF IRI
      And its authority-issued release identifier is scoped to that constraint set
      And the release identifier is not treated as a service build or development-iteration identifier
      And its statements are stored in an explicitly identified named graph
      And the named graph is part of the shared governed-constraint dataset
      And representing another release does not create an isolated RDF dataset

    @IT-31R1S2
    Scenario: Keep canonical constraint identity separate from release-specific definitions
      Given the same governed requirement occurs in more than one constraint-set release
      When those releases are represented internally
      Then one stable RDF IRI identifies the canonical constraint
      And each release has a distinct RDF IRI for its release-specific definition
      And every release-specific definition identifies the release in which it occurs
      And no definition overwrites another definition

    @IT-31R1S3
    Scenario: Identify governed resources independently of RDF serialization
      Given a governed release, constraint, definition, authority, acquisition, or executable artifact requires identity
      When that resource is represented internally
      Then it is identified by a governed RDF IRI
      And its identity is not derived from a transport filename or directory
      And its identity does not depend on a runtime-generated blank node

  @IT-31R2
  Rule: Treat constraint files as content-addressed RDF transport artifacts

    @IT-31R2S1
    Scenario Outline: Load a supported RDF dataset serialization
      Given a constraint transport artifact is serialized as <serialization>
      And its filename contains the SHA-256 digest of its exact bytes
      When the artifact is loaded
      Then the computed artifact digest must match its filename
      And every named graph in the artifact is retained in the staging dataset
      And the transport artifact is recorded in the RDF catalog

      Examples:
        | serialization |
        | TriG          |
        | N-Quads       |

    @IT-31R2S2
    Scenario: Reject a constraint artifact whose content does not match its name
      Given a constraint transport artifact has a content-addressed filename
      And the SHA-256 digest of its bytes does not match that filename
      When the artifact is loaded
      Then the artifact is rejected
      And none of its graphs are added to the governed-constraint dataset

    @IT-31R2S3
    Scenario: Infer no constraint meaning from a transport name or location
      Given a constraint transport artifact has been supplied for loading
      When its constraint domain, authority, constraint set, release identifier, classification, and applicability are determined
      Then those facts are read from governed RDF statements and registered source evidence
      And no such fact is inferred from its filename, directory, or acquisition location

  @IT-31R3
  Rule: Resolve constraint relationships across the entire RDF dataset

    @IT-31R3S1
    Scenario: Resolve a constraint reference across named graphs
      Given one named graph contains a governed constraint definition
      And that definition references a resource described in another named graph
      When the staged constraint dataset is resolved
      Then the reference is resolved by the resource's RDF IRI
      And the relationship is preserved across the named-graph boundary

    @IT-31R3S2
    Scenario: Resolve references independently of transport loading order
      Given two constraint transport artifacts contain named graphs that reference one another
      When the artifacts are loaded in either order
      Then resolution produces the same governed RDF dataset
      And a forward reference is not rejected before all staged artifacts have been loaded

    @IT-31R3S3
    Scenario: Reject an unresolved governed-resource reference
      Given all selected constraint artifacts have been loaded into the staging dataset
      And a governed constraint definition references an RDF IRI that cannot be resolved
      When the staged dataset is verified
      Then activation is rejected
      And the unresolved IRI and referring definition are reported for governance review

    @IT-31R3S4
    Scenario Outline: Relate independently identified constraint-set releases
      Given two governed constraint-set releases each retain their own authority-issued release identifier
      When one release <release relationship> the other release
      Then the relationship is represented explicitly by their RDF IRIs
      And neither release adopts the other release's identifier as its own
      And constraints in either release may reference governed resources in the other release

      Examples:
        | release relationship |
        | overlays             |
        | requires             |
        | is compatible with   |
        | supersedes           |

  @IT-31R4
  Rule: Enforce one governed RDF structure for every constraint source

    @IT-31R4S1
    Scenario: Validate a supplied constraint dataset against the constraint-model shapes
      Given one or more constraint artifacts have been loaded into the staging dataset
      When their internal RDF structure is verified
      Then every release identifies its constraint domain, authority, constraint set, authority-issued release identifier, classification, and source provenance
      And every release-specific definition identifies one canonical constraint and one release
      And every definition identifies its target in the applicable governed RDF domain model
      And every definition identifies an executable artifact or an inactive-for-review disposition
      And the staging dataset conforms to the governed constraint-model shapes

    @IT-31R4S2
    Scenario: Preserve source-native location syntax as provenance rather than RDF behavior
      Given a source constraint contains a source-native location such as an XPath
      When its definition is represented in the constraint dataset
      Then the source-native location is retained as source-location evidence
      And that location is not treated as an RDF query or executable constraint

    @IT-31R4S3
    Scenario: Reject a structurally invalid constraint dataset
      Given a staged constraint dataset does not conform to the governed constraint-model shapes
      When activation is requested
      Then activation is rejected
      And every structural validation failure is reported for governance review
      And the active governed-constraint dataset remains unchanged

  @IT-31R5
  Rule: Preserve complete provenance without confusing source and transport identity

    @IT-31R5S1
    Scenario: Trace a release-specific definition to authoritative source evidence
      Given an authoritative source record has been normalized as a release-specific constraint definition
      When the definition is stored in the governed-constraint dataset
      Then it identifies the source artifact, issuer or issuers, authority-issued release identifier, and source content digest
      And it identifies the worksheet or section and row or record location
      And it retains the original source values, message, severity, rule logic, and source location

    @IT-31R5S2
    Scenario: Keep source and transport digests distinct
      Given a constraint release was compiled from an authoritative source artifact
      And the resulting RDF was supplied in a transport artifact
      When their provenance is recorded
      Then the source content digest identifies the authoritative input
      And the artifact digest identifies the exact transported RDF bytes
      And neither digest is substituted for the other

    @IT-31R5S3
    Scenario: Record every graph contributed by a transport artifact
      Given one constraint transport artifact contains one or more named graphs
      When the artifact is accepted
      Then the RDF catalog identifies every named graph obtained from that artifact
      And each graph retains its own governed RDF identity

  @IT-31R6
  Rule: Change the active constraint dataset atomically

    @IT-31R6S1
    Scenario: Activate a completely verified staged dataset
      Given every selected artifact has been loaded into the staging dataset
      And its structure, references, provenance, and executable dispositions are valid
      When the staged dataset is activated
      Then all of its accepted named graphs become available together
      And the active dataset records the activation identity and time
      And validations can identify the exact active graphs and constraint-set releases they used

    @IT-31R6S2
    Scenario: Prevent partial activation
      Given any selected graph fails structural validation or reference resolution
      When activation is requested
      Then none of the staged graphs become active
      And the previously active governed-constraint dataset remains unchanged

    @IT-31R6S3
    Scenario: Reject conflicting statements about a governed identity
      Given staged artifacts make incompatible governed statements about the same RDF IRI
      When the staging dataset is verified
      Then activation is rejected
      And the conflicting statements and contributing artifacts are reported for governance review

  @IT-31R7
  Rule: Run one service build with any conforming governed constraint dataset

    @IT-31R7S1
    Scenario: Change constraint content without changing service code
      Given two governed-constraint datasets both conform to the constraint-model shapes
      And the datasets contain different releases, definitions, or governed overlays
      When either dataset is activated for the same service build
      Then the service loads and evaluates its active executable constraints
      And no constraint-specific Python code or service rebuild is required

    @IT-31R7S2
    Scenario: Compose active constraints by RDF identity
      Given active base and governed-overlay graphs in a constraint domain are applicable to a validation cycle
      When the cycle's effective constraints are composed
      Then constraints and their relationships are resolved by RDF IRI across the active dataset
      And canonical constraints are deduplicated by their governed RDF identity
      And graph filenames and loading order do not affect the composition

    @IT-31R7S3
    Scenario: Trace a finding through the shared constraint dataset
      Given an active executable constraint produces a validation finding
      When the finding is recorded
      Then it identifies the executable artifact and exact release-specific definition
      And the definition identifies its canonical constraint and constraint-set release
      And its authoritative source evidence is retrievable across the governed RDF dataset
