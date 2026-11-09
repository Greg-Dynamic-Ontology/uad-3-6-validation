"""IT-64R3S1: commit related customer resources together."""

import os
from pathlib import Path
from uuid import uuid4
from urllib.parse import parse_qs, urlsplit

import pytest

from owb_graphdb.client import GraphDBClient
from owb_graphdb.configuration import RepositoryConfiguration
from owb_graphdb.setup import setup_repository

from rdflib import Graph, Literal, Namespace, URIRef
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
    sh:class customer:CustomerAccount ;
    sh:property [ sh:path customer:name ; sh:minCount 1 ;
                  sh:maxCount 1 ; sh:datatype xsd:string ] ;
    sh:property [ sh:path customer:createdAt ; sh:minCount 1 ;
                  sh:maxCount 1 ; sh:datatype xsd:dateTime ] .

test:Membership a sh:NodeShape ;
    sh:targetClass customer:Membership ;
    sh:property [ sh:path customer:account ; sh:node test:Account ; sh:minCount 1 ;
                  sh:maxCount 1 ; sh:nodeKind sh:IRI ] ;
    sh:property [ sh:path customer:user ; sh:minCount 1 ;
                  sh:maxCount 1 ; sh:nodeKind sh:IRI ] ;
    sh:property [ sh:path customer:role ; sh:minCount 1 ;
                  sh:maxCount 1 ; sh:nodeKind sh:IRI ] .
"""


@pytest.fixture
def customer_test_repository_url(tmp_path):
    """Provision an owned repository with this scenario's relationship shape."""
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
            shapes_version="it64-r3-s1-test-v1",
            data_graph_iris=("urn:uad:test:it64:r3:s1:customer",),
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

def test_it_64_r3_s1_commit_related_resources_together(customer_test_repository_url):
    repository_url = customer_test_repository_url
    graph_iri = "urn:uad:test:it64:r3:s1:customer"
    customer = Namespace("urn:uad:customer:")
    account_id = URIRef("urn:uad:test:account:it64-r3-s1")
    user_id = URIRef("urn:uad:test:user:it64-r3-s1")
    membership = URIRef("urn:uad:test:membership:it64-r3-s1")
    proposed = Graph()
    proposed.add((account_id, RDF.type, customer.CustomerAccount))
    proposed.add((account_id, customer.name, Literal("Atomic account", datatype=XSD.string)))
    proposed.add((account_id, customer.createdAt, Literal(
        "2026-11-05T12:00:00Z", datatype=XSD.dateTime,
    )))
    proposed.add((user_id, RDF.type, customer.User))
    proposed.add((membership, RDF.type, customer.Membership))
    proposed.add((membership, customer.account, account_id))
    proposed.add((membership, customer.user, user_id))
    proposed.add((membership, customer.role, customer.Owner))

    observer = CustomerRdfStore(repository_url, graph_iri)
    assert len(observer.retrieve()) == 0, "The owned test graph must start empty."
    snapshots = []
    commit_urls = []

    class ObservedStore(CustomerRdfStore):
        """Observe actual reads at transaction boundaries without mocking GraphDB."""

        def _request(self, method, url, **kwargs):
            parsed = urlsplit(url)
            action = parse_qs(parsed.query).get("action", [None])[0]
            is_transaction_write = method == "PUT" and "/transactions/" in parsed.path
            if is_transaction_write and action == "COMMIT":
                commit_urls.append(url.split("?", 1)[0])
                snapshots.append(("before commit", observer.retrieve()))
            response = super()._request(method, url, **kwargs)
            if is_transaction_write and action in {"ADD", "UPDATE"}:
                snapshots.append((f"after {action}", observer.retrieve()))
            return response

    writer = ObservedStore(repository_url, graph_iri)
    writer.commit(proposed, actor_id="urn:uad:test:system:it64-r3-s1")

    assert len(commit_urls) == 1, (
        "The related account and owner membership must use one transaction commit."
    )
    assert any(stage == "after ADD" for stage, _ in snapshots), (
        "The test must observe a separate reader after RDF is staged in the transaction."
    )
    for stage, visible in snapshots:
        assert len(visible) == 0, (
            f"IT-64R3S1: a separate reader saw {len(visible)} customer triples "
            f"{stage}, before the related-resource transaction was committed."
        )

    actual = CustomerRdfStore(repository_url, graph_iri).retrieve()
    assert (account_id, RDF.type, customer.CustomerAccount) in actual
    assert (membership, RDF.type, customer.Membership) in actual
    assert (membership, customer.account, account_id) in actual
    assert (membership, customer.role, customer.Owner) in actual
    assert isomorphic(_normalized_strings(proposed), _normalized_strings(actual)), (
        "IT-64R3S1 requires the complete account and owner membership to become "
        "available together after the successful transaction commit."
    )
