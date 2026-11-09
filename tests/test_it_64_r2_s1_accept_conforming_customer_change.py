"""IT-64R2S1: accept a change that leaves customer RDF conforming."""

import os
from pathlib import Path
from uuid import uuid4

import pytest

from owb_graphdb.client import GraphDBClient
from owb_graphdb.configuration import RepositoryConfiguration
from owb_graphdb.setup import setup_repository

from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.compare import isomorphic
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
            shapes_version="it64-r2-s1-test-v1",
            data_graph_iris=("urn:uad:test:it64:r2:s1:customer",),
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

def test_it_64_r2_s1_accept_conforming_customer_change(customer_test_repository_url):
    repository_url = customer_test_repository_url
    graph_iri = "urn:uad:test:it64:r2:s1:customer"
    customer = Namespace("urn:uad:customer:")
    account_id = URIRef("urn:uad:test:account:it64-r2-s1")
    user_id = URIRef("urn:uad:test:user:it64-r2-s1")
    membership = BNode()
    old_name = Literal("Original customer name", datatype=XSD.string)
    new_name = Literal("Updated customer name", datatype=XSD.string)

    initial = Graph()
    initial.add((account_id, RDF.type, customer.CustomerAccount))
    initial.add((account_id, customer.name, old_name))
    initial.add((account_id, customer.createdAt, Literal(
        "2026-11-05T12:00:00Z", datatype=XSD.dateTime,
    )))
    initial.add((user_id, RDF.type, customer.User))
    initial.add((membership, RDF.type, customer.Membership))
    initial.add((membership, customer.account, account_id))
    initial.add((membership, customer.user, user_id))
    initial.add((membership, customer.role, customer.Owner))

    # Given: a conforming dataset has actually been committed and read back.
    writer = CustomerRdfStore(repository_url, graph_iri)
    writer.commit(initial, actor_id="urn:uad:test:system:it64-r2-s1")
    stored = CustomerRdfStore(repository_url, graph_iri).retrieve()
    assert isomorphic(_normalized_strings(initial), _normalized_strings(stored)), (
        "Prerequisite failed: the initial conforming dataset was not persisted."
    )

    # Propose the resulting dataset using the existing whole-graph commit API.
    # Replacing the sole name preserves its xsd:string and min/maxCount rules.
    proposed = Graph()
    for triple in stored:
        proposed.add(triple)
    proposed.set((account_id, customer.name, new_name))

    # When: normal return confirms GraphDB accepted the transaction commit.
    writer.commit(proposed, actor_id="urn:uad:test:system:it64-r2-s1")

    # Then: a separate reader observes the change and all retained RDF.
    actual = CustomerRdfStore(repository_url, graph_iri).retrieve()
    comparable = _normalized_strings(actual)
    assert (account_id, customer.name, new_name) in comparable, (
        "IT-64R2S1 requires the accepted customer change to be readable."
    )
    assert (account_id, customer.name, old_name) not in comparable, (
        "The committed name replacement must remove the previous value."
    )
    assert isomorphic(_normalized_strings(proposed), comparable), (
        "IT-64R2S1 requires the complete conforming result of the change "
        "to be available to subsequent reads."
    )
