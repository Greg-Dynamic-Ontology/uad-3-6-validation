"""IT-64R5S2: reject a customer change without an attributable actor."""

import os
from pathlib import Path
from uuid import uuid4
from urllib.parse import urlencode
from urllib.request import Request, urlopen

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
            shapes_version="it64-r5-s2-test-v1",
            data_graph_iris=("urn:uad:test:it64:r5:s2:customer",),
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

PROV = Namespace("http://www.w3.org/ns/prov#")
CHANGE = Namespace("urn:uad:customer:change:")
PROVENANCE_GRAPH = "urn:uad:customer:provenance"


def _read_graph(repository_url, graph_iri):
    """Read persisted RDF using an independent HTTP connection."""
    query = urlencode({"context": URIRef(graph_iri).n3(), "infer": "false"})
    request = Request(
        repository_url + "/statements?" + query,
        headers={"Accept": "application/n-triples"},
    )
    with urlopen(request, timeout=30) as response:
        body = response.read()
    return Graph().parse(data=body.decode("utf-8"), format="nt")


def test_it_64_r5_s2_reject_change_without_attributable_actor(customer_test_repository_url):
    repository_url = customer_test_repository_url
    graph_iri = "urn:uad:test:it64:r5:s2:customer"
    customer = Namespace("urn:uad:customer:")
    account = URIRef("urn:uad:test:account:it64-r5-s2")
    user = URIRef("urn:uad:test:user:it64-r5-s2")
    membership = URIRef("urn:uad:test:membership:it64-r5-s2")
    old_name = Literal("Original account", datatype=XSD.string)
    initial = Graph()
    initial.add((account, RDF.type, customer.CustomerAccount))
    initial.add((account, customer.name, old_name))
    initial.add((account, customer.createdAt, Literal(
        "2026-11-05T12:00:00Z", datatype=XSD.dateTime,
    )))
    initial.add((user, RDF.type, customer.User))
    initial.add((membership, RDF.type, customer.Membership))
    initial.add((membership, customer.account, account))
    initial.add((membership, customer.user, user))
    initial.add((membership, customer.role, customer.Owner))
    CustomerRdfStore(repository_url, graph_iri).commit(
        initial, actor_id="urn:uad:test:system:it64-r5-s2",
    )
    before = _read_graph(repository_url, graph_iri)
    assert isomorphic(_normalized_strings(initial), _normalized_strings(before))
    attribution_before = _read_graph(repository_url, PROVENANCE_GRAPH)

    additions = Graph()
    additions.add((account, customer.name, Literal("Unattributed change", datatype=XSD.string)))
    removals = Graph()
    removals.add((account, customer.name, old_name))
    proposed = initial - removals + additions

    class ObservedStore(CustomerRdfStore):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.requests = []

        def _request(self, method, url, **kwargs):
            self.requests.append(method)
            return super()._request(method, url, **kwargs)

    # Exercise both write entry points. No actor includes omission, null,
    # empty text, and whitespace. The seed commit above has an identified actor.
    cases = [
        ("omitted", {}, TypeError),
        ("null", {"actor_id": None}, ValueError),
        ("empty", {"actor_id": ""}, ValueError),
        ("whitespace", {"actor_id": "   "}, ValueError),
    ]
    for operation in ("commit", "apply_change"):
        for label, actor_arguments, expected_error in cases:
            writer = ObservedStore(repository_url, graph_iri)
            with pytest.raises(expected_error):
                if operation == "commit":
                    writer.commit(proposed, **actor_arguments)
                else:
                    writer.apply_change(
                        additions=additions, removals=removals, **actor_arguments,
                    )
            assert not writer.requests, (
                f"{operation} with {label} actor must be rejected before contacting GraphDB."
            )
            actual = _read_graph(repository_url, graph_iri)
            assert isomorphic(_normalized_strings(before), _normalized_strings(actual)), (
                f"IT-64R5S2: {operation} with {label} actor changed stored customer RDF."
            )
            attribution_after = _read_graph(repository_url, PROVENANCE_GRAPH)
            assert isomorphic(
                _normalized_strings(attribution_before), _normalized_strings(attribution_after),
            ), "Rejecting an unattributed change must not create a durable change record."
