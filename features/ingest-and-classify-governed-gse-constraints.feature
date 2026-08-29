Feature: Ingest and classify governed GSE constraint sources
  As a validation service operator
  I want every GSE constraint to be derived from explicit authoritative source evidence
  So that Fannie Mae-only, Freddie Mac-only, and shared constraints are classified without guesswork or duplication

  Background:
    Given authoritative GSE constraint sources are centrally registered and versioned

  @IT-30R1
  Rule: Determine GSE authority from governed source evidence

    @IT-30R1S1
    Scenario: Recognize a jointly issued GSE constraint source
      Given an authoritative constraint source identifies both Fannie Mae and Freddie Mac as its issuers
      When the source is registered
      Then the source is governed as a shared GSE constraint source
      And its constraints are classified as shared unless explicit authoritative evidence says otherwise
      And its authority is not inferred from the folder in which a copy was acquired

    @IT-30R1S2
    Scenario Outline: Recognize a constraint source issued by one GSE
      Given an authoritative constraint source explicitly identifies <issuing GSE> as its sole issuer
      When the source is registered
      Then the source is governed as an <classification> constraint source
      And its constraints are not classified for the other GSE without additional authoritative evidence

      Examples:
        | issuing GSE  | classification    |
        | Fannie Mae   | Fannie Mae-only   |
        | Freddie Mac  | Freddie Mac-only  |

    @IT-30R1S3
    Scenario: Exclude experimental material from authoritative constraint ingestion
      Given material is stored under the experimental specs/UAD location
      When authoritative GSE constraint sources are discovered
      Then the experimental material is excluded
      And it cannot establish a constraint's authority, classification, or active version
      And its existence does not override an authoritative source

    @IT-30R1S4
    Scenario: Refuse to guess an ambiguous GSE authority
      Given a candidate constraint source does not contain sufficient governed evidence of its issuing authority
      When the source is registered
      Then authoritative registration is rejected
      And no constraint from the source is classified as Fannie Mae-only, Freddie Mac-only, or shared
      And the ambiguity is reported for governance review

  @IT-30R2
  Rule: Preserve one canonical constraint identity with complete source provenance

    @IT-30R2S1
    Scenario: Treat identical authoritative copies of a joint release as one constraint set
      Given the same jointly issued constraint release was acquired from both Fannie Mae and Freddie Mac
      And the acquired artifacts have the same content digest
      When the authoritative sources are ingested
      Then one canonical shared GSE constraint set is registered
      And each constraint in the release is registered once by canonical identity
      And both authoritative acquisition locations are retained as provenance

    @IT-30R2S2
    Scenario: Keep different releases distinct even when constraint identifiers repeat
      Given two authoritative releases contain the same constraint message identifier
      And the releases have different governed versions or content digests
      When the releases are ingested
      Then each release remains a distinct versioned constraint set
      And the constraint definition from each release retains its own source content and provenance
      And activating one release does not rewrite the other release

    @IT-30R2S3
    Scenario: Trace a classified constraint to its authoritative evidence
      Given a GSE constraint has been classified and registered
      When its governance record is requested
      Then the record identifies its canonical constraint identity
      And the record identifies whether it is Fannie Mae-only, Freddie Mac-only, or shared
      And the record identifies the authoritative source document, issuer, version, and content digest
      And the record identifies the original source location within the document
