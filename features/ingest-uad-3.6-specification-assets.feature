Feature: Ingest UAD 3.6 specification assets

As a compliance service operator
I want to ingest the GSE trimmed UAD 3.6 schema and related specification details
So that the validation service is based on governed, versioned source material

Background:
Given the service supports UAD 3.6
And stable IRIs can be minted for UAD schema components, XML instance nodes, predicates, and validation rules

Scenario: Load the GSE trimmed schema into the graph store
Given a published GSE trimmed UAD 3.6 schema file
When the schema ingestion process runs
Then schema elements are represented as graph resources
And schema datatypes are represented as graph resources
And schema enumerations are represented as controlled values
And each schema component has a stable IRI
And the source schema version is recorded

Scenario: Load Appendix A mapping and XLink requirements
Given the UAD 3.6 Appendix A mapping details
When the mapping ingestion process runs
Then XLink relationship requirements are represented as graph predicates
And allowed subject and object resource types are recorded
And each relationship predicate has a stable IRI
And each mapping rule is traceable to its source location

Scenario: Load Appendix H rules
Given the UAD 3.6 Appendix H rules
When the rule ingestion process runs
Then each rule is represented as a validation rule resource
And each rule has a stable rule identifier
And each rule records its severity
And each rule records whether it applies to Fannie Mae, Freddie Mac, or both
And each rule is traceable to its source location

Scenario: Preserve source provenance
Given any ingested schema component, mapping rule, value set, or validation rule
When the resource is queried
Then the response includes the source document name
And the source version
And the source section or appendix reference
And the ingestion timestamp
