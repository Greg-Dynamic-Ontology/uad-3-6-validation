"""IT-64R7S2: report and reconcile an uncertain commit outcome."""

import os
from pathlib import Path
from uuid import uuid4
from urllib.parse import urlencode, parse_qs, urlsplit
from urllib.error import URLError
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
    sh:targetClass customer:CustomerAccount ;
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
            shapes_version="it64-r7-s2-test-v1",
            data_graph_iris=("urn:uad:test:it64:r7:s2:customer",),
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


def test_it_64_r7_s2_report_uncertain_commit_outcome(customer_test_repository_url):
    repository_url = customer_test_repository_url
    graph_iri = "urn:uad:test:it64:r7:s2:customer"
    customer = Namespace("urn:uad:customer:")
    account = URIRef("urn:uad:test:account:it64-r7-s2")
    user = URIRef("urn:uad:test:user:it64-r7-s2")
    membership = URIRef("urn:uad:test:membership:it64-r7-s2")
    proposed = Graph()
    proposed.add((account, RDF.type, customer.CustomerAccount))
    proposed.add((account, customer.name, Literal("Unconfirmed account", datatype=XSD.string)))
    proposed.add((account, customer.createdAt, Literal(
        "2026-11-05T12:00:00Z", datatype=XSD.dateTime,
    )))
    proposed.add((user, RDF.type, customer.User))
    proposed.add((membership, RDF.type, customer.Membership))
    proposed.add((membership, customer.account, account))
    proposed.add((membership, customer.user, user))
    proposed.add((membership, customer.role, customer.Owner))
    lost_response = URLError(ConnectionResetError("Simulated loss of commit response"))

    class LostCommitResponseStore(CustomerRdfStore):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.commit_requests = []
            self.rollback_requests = []
            self.change_iri = None
            self.response_lost = False

        def _request(self, method, url, **kwargs):
            query = parse_qs(urlsplit(url).query)
            action = query.get("action", [None])[0]
            if method == "DELETE" and "/transactions/" in urlsplit(url).path:
                self.rollback_requests.append(url)
            if method == "PUT" and action == "ADD" and query.get("context") == [URIRef(PROVENANCE_GRAPH).n3()]:
                record = Graph().parse(data=kwargs["body"].decode("utf-8"), format="nt")
                activities = list(record.subjects(RDF.type, PROV.Activity))
                assert len(activities) == 1
                self.change_iri = str(activities[0])
            if method == "PUT" and action == "COMMIT":
                self.commit_requests.append(url.split("?", 1)[0])
                # Commit really happens. Only the successful response is hidden
                # from the application, reproducing the ambiguous network case.
                response = super()._request(method, url, **kwargs)
                assert response[0] in {200, 204}
                self.response_lost = True
                raise lost_response
            return super()._request(method, url, **kwargs)

    writer = LostCommitResponseStore(repository_url, graph_iri)
    failure = None
    try:
        writer.commit(proposed, actor_id="urn:uad:test:system:it64-r7-s2")
    except Exception as error:
        failure = error
    try:
        assert writer.response_lost, "The test must reach the real successful GraphDB commit."
        assert failure is not None, "Losing the commit response must not return success."
        assert getattr(failure, "code", None) == "commit_outcome_unconfirmed", (
            "IT-64R7S2 requires commit_outcome_unconfirmed when the commit response "
            f"is lost; received {type(failure).__name__}."
        )
        assert hasattr(failure, "committed") and failure.committed is None
        assert getattr(failure, "rollback_confirmed", None) is False
        assert getattr(failure, "reconciliation_required", None) is True
        assert getattr(failure, "transaction_url", None) == writer.commit_requests[0]
        assert getattr(failure, "change_iri", None) == writer.change_iri
        assert "unconfirmed" in str(failure).lower()
        assert len(writer.commit_requests) == 1, "Do not automatically retry an uncertain commit."
        assert not writer.rollback_requests, (
            "Do not attempt rollback after losing the commit response: it may already be committed."
        )

        # Reconciliation must use durable evidence, even from a new adapter.
        class ReconciliationReader(CustomerRdfStore):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.methods = []

            def _request(self, method, url, **kwargs):
                self.methods.append(method)
                return super()._request(method, url, **kwargs)

        reader = ReconciliationReader(repository_url, graph_iri)
        reconcile = getattr(reader, "reconcile_change", None)
        assert callable(reconcile), "IT-64R7S2 requires reconcile_change(change_iri=...)."
        resolution = reconcile(change_iri=failure.change_iri)
        assert isinstance(resolution, dict), "Reconciliation must return a machine-readable result."
        assert resolution.get("outcome") == "committed"
        assert resolution.get("change_iri") == failure.change_iri
        assert resolution.get("retry_allowed") is False, "A confirmed committed change must not be replayed."
        assert reader.methods and set(reader.methods) == {"GET"}, (
            "Reconciliation must inspect persisted evidence without replaying the write."
        )
        actual = _read_graph(repository_url, graph_iri)
        assert isomorphic(_normalized_strings(proposed), _normalized_strings(actual))
        records = _read_graph(repository_url, PROVENANCE_GRAPH)
        assert set(records.subjects(RDF.type, PROV.Activity)) == {URIRef(failure.change_iri)}, (
            "The lost response must not cause duplicate committed attribution records."
        )
        # Missing evidence is not proof of rollback and cannot authorize retry.
        unknown = reconcile(change_iri=f"urn:uad:customer-change:{uuid4()}")
        assert unknown.get("outcome") == "unconfirmed"
        assert unknown.get("retry_allowed") is False
    finally:
        close = getattr(failure, "close", None)
        if callable(close):
            close()
