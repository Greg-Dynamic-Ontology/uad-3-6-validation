                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        Feature: Govern schema source identities with IRIs

  Schema documents may be loaded from a repository, an extracted archive,
  an upload, a temporary directory, or another operating system. Persistent
  RDF must identify the source document without preserving the machine-specific
  location from which that document happened to be loaded.

  @IT-8R2
  Rule: A schema source identity is independent of its storage location

    @IT-8R2S1
    Scenario: Assign a governed IRI to a schema source
      Given a schema document accepted for processing
      When its source identity is assigned
      Then the source identity is an absolute governed IRI
      And the IRI is minted under the configured authority
      And the IRI contains no machine-specific file-system information

    @IT-8R2S2
    Scenario: Recognize the same schema document in different locations
      Given identical schema content is available from two physical locations
      When a source identity is assigned from each location
      Then both copies receive the same governed IRI
      And neither physical location contributes to that IRI

    @IT-8R2S3
    Scenario: Distinguish different schema documents with the same file name
      Given two schema documents have the same file name
      And the schema documents have different content
      When a source identity is assigned to each document
      Then the schema documents receive different governed IRIs

  @IT-8R3
  Rule: Source identity and source location are separate concerns

    @IT-8R3S1
    Scenario: Resolve a governed IRI to an available schema document
      Given a governed schema source IRI
      And a source catalog associates that IRI with an available document
      When the schema source is requested
      Then the document is obtained through the source catalog
      And the governed IRI remains the document identity

    @IT-8R3S2
    Scenario: Move a schema document without changing its identity
      Given a governed schema source IRI resolves to a physical document
      When the physical document is moved without changing its content
      And the source catalog is updated
      Then the governed IRI remains unchanged
      And the governed IRI resolves to the new location

    @IT-8R3S3
    Scenario: Report a governed schema source that cannot be resolved
      Given a governed schema source IRI
      And no available document is registered for that IRI
      When the schema source is requested
      Then processing stops before the schema document is used
      And a business error identifies the unresolved schema source
      And a technical error identifies the failed resolution operation

  @IT-8R4
  Rule: Governed source identity is deterministic and auditable

    @IT-8R4S1
    Scenario: Reassign the identity of unchanged schema content
      Given a schema document has a governed source IRI
      When its source identity is assigned again under the same minting policy
      Then the same governed IRI is produced

    @IT-8R4S2
    Scenario: Record evidence supporting a governed source identity
      Given a governed IRI is assigned to a schema document
      When source-identity provenance is recorded
      Then the provenance records the governed IRI
      And the provenance records a digest of the source content
      And the provenance records the minting-policy version
      And the provenance may record a physical locator separately

    @IT-8R4S3
    Scenario: Serialize source traceability without serializing its locator
      Given a Logical Schema Model refers to a governed schema source
      And a physical locator was used to load that source
      When the Logical Schema Model is serialized as RDF
      Then source traceability uses the governed IRI
      And the physical locator is not serialized as the source identity
      And no user-specific or machine-specific directory is disclosed
