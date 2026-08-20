Feature: Govern schema-source identities in a knowledge graph

  The Milestone 1 Logical Schema graph contains schema-source identities
  minted under a provisional namespace. ADR-0017 establishes the governed
  UAD schema-source namespace. The namespace-correction operator must produce
  a canonical knowledge graph without changing the knowledge that is not
  governed by that migration.

  The executable API is namespace_correction.apply(kg_in: Graph) -> Graph.
  A successful call returns a new graph and does not modify kg_in. A failed
  call raises NamespaceCorrectionError and returns no output graph. The error
  carries error_code, reason_code, candidate_iri, operator_iri,
  business_message, and technical_message.

  @IT-9R1
  Rule: The namespace-correction contract is governed knowledge

    @IT-9R1S1
    Scenario: Describe namespace correction as a knowledge-graph operator
      Given the namespace-correction operator is available
      When its operator contract is loaded
      Then the contract identifies the operator with a governed IRI
      And the contract identifies RDF graphs as its input and output
      And the contract identifies the provisional schema-source namespace
      And the contract identifies the governed UAD schema-source namespace
      And the contract identifies ADR-0017 as the governing identity decision
      And the contract identifies ADR-0018 as the governing knowledge-organization decision
      And the contract declares that the operator is deterministic and idempotent

    @IT-9R1S2
    Scenario: Validate input and output requirements independently
      Given the namespace-correction conformance shapes
      And a valid input graph containing a provisional schema-source IRI
      And a malformed input graph containing an invalid provisional schema-source candidate
      And a valid output graph containing at least one schema-source IRI
      And every schema-source IRI in the valid output graph uses the governed UAD schema-source namespace
      And an invalid output graph retaining a provisional schema-source IRI
      When the input fixture graphs are validated directly against the input shape
      And the output fixture graphs are validated directly against the output shape
      Then the valid input graph conforms to the input shape
      And the malformed input graph does not conform to the input shape
      And the valid output graph conforms to the output shape
      And the invalid output graph does not conform to the output shape
      And no namespace-correction transformation is executed during shape validation

  @IT-9R2
  Rule: Provisional schema-source identities are corrected deliberately

    @IT-9R2S1
    Scenario: Correct a provisional schema-source IRI
      Given a knowledge graph containing a valid provisional schema-source IRI
      When the namespace-correction operator runs
      Then the output graph contains the governed UAD schema-source IRI
      And the SHA-256 digest is preserved
      And the provisional schema-source IRI is absent from the output graph

    @IT-9R2S2
    Scenario: Correct a schema-source IRI wherever it occurs in an RDF graph
      Given the same valid provisional schema-source IRI occurs as a subject
      And the provisional schema-source IRI occurs as a predicate
      And the provisional schema-source IRI occurs as an object
      When the namespace-correction operator runs
      Then every occurrence is replaced by the governed UAD schema-source IRI
      And no occurrence of the provisional schema-source IRI remains
      And the subject occurrence remains a subject
      And the predicate occurrence remains a predicate
      And the object occurrence remains an object

    @IT-9R2S3
    Scenario: Correct the complete Milestone 1 Logical Schema graph
      Given the complete Milestone 1 Logical Schema graph
      And the set of provisional schema-source IRIs in the graph is not empty
      When the namespace-correction operator runs
      Then the output schema-source IRI set equals the union of the governed schema-source IRIs already in the input and the governed mapping of the provisional schema-source IRIs in the input
      And every input triple containing a provisional schema-source IRI has exactly one term-for-term governed counterpart in the output
      And the output contains no IRI under the provisional schema-source namespace

  @IT-9R3
  Rule: Namespace correction preserves knowledge outside its authority

    @IT-9R3S1
    Scenario: Preserve unaffected RDF statements
      Given a knowledge graph containing provisional schema-source IRIs
      And the graph contains an unaffected RDF statement
      And an unaffected statement contains no provisional schema-source IRI in its subject, predicate, or object
      When the namespace-correction operator runs
      Then every unaffected RDF statement is unchanged in the output graph
      And the input graph remains unchanged

    @IT-9R3S2
    Scenario: Preserve the content-addressed source identity
      Given a provisional schema-source IRI contains a valid SHA-256 digest
      When the namespace-correction operator runs
      Then the governed schema-source IRI contains the same SHA-256 digest
      And no file name or physical location is introduced into the identity

    @IT-9R3S3
    Scenario: Reject a malformed provisional schema-source candidate
      Given a knowledge graph contains a term under the provisional schema-source namespace
      And the term does not contain a valid SHA-256 digest
      And the input RDF triple set has been retained for comparison
      When namespace_correction.apply is called with the input graph
      Then NamespaceCorrectionError is raised
      And error_code is "INVALID_SCHEMA_SOURCE_IRI"
      And reason_code is "INVALID_SHA256_DIGEST"
      And candidate_iri equals the malformed schema-source candidate
      And operator_iri equals the governed namespace-correction operator IRI
      And business_message is "The schema-source identity is invalid."
      And technical_message contains candidate_iri
      And technical_message contains "64-character lowercase hexadecimal SHA-256 digest"
      And the input RDF triple set remains exactly unchanged
      And no output graph is returned

  @IT-9R4
  Rule: Namespace correction is deterministic and idempotent

    @IT-9R4S1
    Scenario: Reprocess the same provisional knowledge graph
      For this scenario, equivalent means exact equality of the asserted RDF
      triple sets. Blank-node isomorphism and entailment-based equivalence are
      not used because the input and required outputs are ground RDF graphs.

      Given the same ground RDF graph containing provisional schema-source IRIs
      And the same namespace-correction operator contract and policy version
      When two independent executions process the input graph
      Then neither output graph contains a blank node
      And the first output RDF triple set exactly equals the second output RDF triple set
      And the set of governed schema-source IRIs is exactly equal in both outputs

    @IT-9R4S2
    Scenario: Process an already corrected knowledge graph
      Given a knowledge graph contains at least one schema-source IRI
      And every schema-source IRI uses the governed UAD schema-source namespace
      When the namespace-correction operator runs
      Then the output RDF triple set exactly equals the input RDF triple set

    @IT-9R4S3
    Scenario: Produce the ground RDF graph required by the operator contract
      Given the input knowledge graph contains no blank nodes
      And the expected output graph is constructed from operator.ttl
      And the expected output graph is constructed without importing or invoking operator.py
      When the namespace-correction operator runs
      Then the output graph contains zero blank nodes
      And the set of expected triples missing from the output is empty
      And the set of output triples absent from the expected graph is empty
