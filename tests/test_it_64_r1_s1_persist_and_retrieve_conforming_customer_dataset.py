"""IT-64R1S1: persist and retrieve customer RDF through GraphDB."""

import os
from pathlib import Path
from uuid import uuid4

import pytest

from owb_graphdb.client import GraphDBClient
from owb_graphdb.configuration import RepositoryConfiguration
from owb_graphdb.setup import setup_repository

from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.compare import graph_diff, isomorphic, to_isomorphic
from rdflib.namespace import RDF, XSD

from app.adapters.customer_rdf_store import CustomerRdfStore


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEST_SHAPES = """
@prefix customer: <urn:uad:customer:> .
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix test: <urn:uad:test:it64:shapes:> .

test:Account a sh:NodeShape ;
    sh:targetClass customer:CustomerAccount ;
    sh:property [ sh:path customer:name ; sh:minCount 1 ;
                  sh:maxCount 1 ; sh:datatype xsd:string ] ;
    sh:property [ sh:path customer:createdAt ; sh:minCount 1 ;
                  sh:maxCount 1 ; sh:datatype xsd:dateTime ] .

test:Membership a sh:NodeShape ;
    sh:targetClass customer:Membership ;
    sh:property [ sh:path customer:account ; sh:minCount 1 ;
                  sh:maxCount 1 ; sh:nodeKind sh:IRI ] ;
    sh:property [ sh:path customer:user ; sh:minCount 1 ;
                  sh:maxCount 1 ; sh:nodeKind sh:IRI ] ;
    sh:property [ sh:path customer:role ; sh:minCount 1 ;
                  sh:maxCount 1 ; sh:nodeKind sh:IRI ] .
"""


@pytest.fixture
def customer_test_repository_url(tmp_path):
    """Own the default repository lifecycle; never delete an explicit override."""
    configured = os.environ.get("UAD_CUSTOMER_RDF_TEST_REPOSITORY_URL", "").strip()
    if configured:
        # Existing opt-in behavior: the operator supplies a dedicated test
        # repository already provisioned with the intended customer shapes.
        yield configured
        return

    server_url = os.environ.get("GRAPHDB_TEST_SERVER_URL", "http://localhost:7200").rstrip("/")
    prefix = "uad-customer-test-it64-"
    repository_id = prefix + uuid4().hex
    client = GraphDBClient(server_url=server_url, timeout_seconds=30)
    template = (
        PROJECT_ROOT / "utilities/graphdb-utilities/tests/fixtures/repository-config.ttl"
    )
    config_graph = Graph().parse(template, format="turtle")
    rep = Namespace("http://www.openrdf.org/config/repository#")
    roots = list(config_graph.subjects(RDF.type, rep.Repository))
    assert len(roots) == 1
    config_graph.set((roots[0], rep.repositoryID, Literal(repository_id)))
    config_path = tmp_path / "repository-config.ttl"
    config_graph.serialize(destination=str(config_path), format="turtle")
    shapes_path = tmp_path / "customer-test-shapes.ttl"
    shapes_path.write_text(TEST_SHAPES, encoding="utf-8")
    result = setup_repository(
        client=client,
        configuration=RepositoryConfiguration(
            server_url=server_url,
            repository_id=repository_id,
            repository_config_path=config_path,
            shapes_path=shapes_path,
            shapes_version="it64-r1-s1-test-v1",
            data_graph_iris=("urn:uad:test:it64:r1:s1:customer",),
        ),
    )
    assert result.success and result.ready, result.message
    try:
        yield f"{server_url}/repositories/{repository_id}"
    finally:
        # Delete exactly the repository created by this fixture, never enumerate
        # or clean other repositories. This also removes its test provenance.
        assert repository_id.startswith(prefix)
        assert len(repository_id.removeprefix(prefix)) == 32
        client.request(method="DELETE", path=f"/rest/repositories/{repository_id}")


def _normalized_strings(graph: Graph) -> Graph:
    """Represent RDF 1.1 plain strings explicitly as xsd:string.

    Preserve language tags, all other datatypes, IRIs, and blank nodes.
    Neither the supplied graph nor the retrieved graph is modified.
    """
    normalized = Graph()
    for subject, predicate, obj in graph:
        if isinstance(obj, Literal) and obj.datatype is None and obj.language is None:
            obj = Literal(str(obj), datatype=XSD.string)
        normalized.add((subject, predicate, obj))
    return normalized

def test_it_64_r1_s1_persist_and_retrieve_conforming_customer_dataset(
    customer_test_repository_url,
):
    repository_url = customer_test_repository_url
    graph_iri = "urn:uad:test:it64:r1:s1:customer"

    # Test-only vocabulary; this test does not define production customer shapes.
    customer = Namespace("urn:uad:customer:")
    account_id = URIRef("urn:uad:test:account:it64-r1-s1")
    user_id = URIRef("urn:uad:test:user:it64-r1-s1")
    membership = BNode()

    expected = Graph()
    expected.add((account_id, RDF.type, customer.CustomerAccount))
    expected.add((
        account_id,
        customer.name,
        Literal("IT-64 test account", datatype=XSD.string),
    ))
    expected.add((
        account_id,
        customer.createdAt,
        Literal("2026-11-05T12:00:00Z", datatype=XSD.dateTime),
    ))
    expected.add((user_id, RDF.type, customer.User))
    expected.add((membership, RDF.type, customer.Membership))
    expected.add((membership, customer.account, account_id))
    expected.add((membership, customer.user, user_id))
    expected.add((membership, customer.role, customer.Owner))

    writer = CustomerRdfStore(repository_url, graph_iri)

    # Normal return means the GraphDB transaction commit succeeded.
    writer.commit(
        expected,
        actor_id="urn:uad:test:system:it64-r1-s1",
    )

    # A separate adapter instance must retrieve the persisted data.
    reader = CustomerRdfStore(repository_url, graph_iri)
    actual = reader.retrieve()

    assert isinstance(actual, Graph)
    expected_comparable = _normalized_strings(expected)
    actual_comparable = _normalized_strings(actual)
    if not isomorphic(expected_comparable, actual_comparable):
        _, missing, unexpected = graph_diff(
            to_isomorphic(expected_comparable), to_isomorphic(actual_comparable),
        )

        def describe(graph):
            return "\n".join(sorted(
                " ".join(term.n3() for term in triple) + " ."
                for triple in graph
            )) or "(none)"

        pytest.fail(
            "Retrieved customer RDF must preserve the committed graph, "
            "including identifiers, relationships, and literal datatypes.\n"
            f"Expected triples: {len(expected)}; retrieved triples: {len(actual)}\n"
            f"Missing triples:\n{describe(missing)}\n"
            f"Unexpected triples:\n{describe(unexpected)}",
            pytrace=False,
        )


