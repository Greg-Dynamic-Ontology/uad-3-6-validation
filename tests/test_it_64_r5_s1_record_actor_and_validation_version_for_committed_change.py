"""IT-64R5S1: persist attribution and validation version atomically."""

import os
from pathlib import Path
from uuid import uuid4
from urllib.parse import parse_qs, urlsplit, urlencode
from urllib.request import Request, urlopen
from datetime import datetime, timezone, timedelta

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
            shapes_version="it64-r5-s1-test-v1",
            data_graph_iris=("urn:uad:test:it64:r5:s1:customer",),
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


def test_it_64_r5_s1_record_actor_and_validation_version_for_committed_change(
    customer_test_repository_url,
):
    repository_url = customer_test_repository_url
    graph_iri = "urn:uad:test:it64:r5:s1:customer"
    customer = Namespace("urn:uad:customer:")
    account = URIRef("urn:uad:test:account:it64-r5-s1")
    user = URIRef("urn:uad:test:user:it64-r5-s1")
    membership = URIRef("urn:uad:test:membership:it64-r5-s1")
    actor = URIRef("urn:uad:test:admin:it64-r5-s1")
    proposed = Graph()
    proposed.add((account, RDF.type, customer.CustomerAccount))
    proposed.add((account, customer.name, Literal("Attributed account", datatype=XSD.string)))
    proposed.add((account, customer.createdAt, Literal(
        "2026-11-05T12:00:00Z", datatype=XSD.dateTime,
    )))
    proposed.add((user, RDF.type, customer.User))
    proposed.add((membership, RDF.type, customer.Membership))
    proposed.add((membership, customer.account, account))
    proposed.add((membership, customer.user, user))
    proposed.add((membership, customer.role, customer.Owner))
    assert len(_read_graph(repository_url, graph_iri)) == 0
    assert len(_read_graph(repository_url, PROVENANCE_GRAPH)) == 0
    snapshots = []
    transaction_urls = set()
    commit_urls = []

    class ObservedStore(CustomerRdfStore):
        def _request(self, method, url, **kwargs):
            parsed = urlsplit(url)
            action = parse_qs(parsed.query).get("action", [None])[0]
            transactional = method == "PUT" and "/transactions/" in parsed.path
            if transactional:
                transaction_urls.add(url.split("?", 1)[0])
                if action == "COMMIT":
                    commit_urls.append(url.split("?", 1)[0])
                    snapshots.append((
                        "before commit", _read_graph(repository_url, graph_iri),
                        _read_graph(repository_url, PROVENANCE_GRAPH),
                    ))
            response = super()._request(method, url, **kwargs)
            if transactional and action == "ADD":
                snapshots.append((
                    "after staging RDF", _read_graph(repository_url, graph_iri),
                    _read_graph(repository_url, PROVENANCE_GRAPH),
                ))
            return response

    started = datetime.now(timezone.utc)
    ObservedStore(repository_url, graph_iri).commit(proposed, actor_id=str(actor))
    finished = datetime.now(timezone.utc)
    assert len(transaction_urls) == 1 and len(commit_urls) == 1, (
        "Customer data and attribution must be written through one transaction."
    )
    assert any(stage == "before commit" for stage, _, _ in snapshots)
    for stage, data, attribution in snapshots:
        assert len(data) == 0 and len(attribution) == 0, (
            f"Neither customer data nor attribution may be visible {stage}."
        )
    actual = _read_graph(repository_url, graph_iri)
    assert isomorphic(_normalized_strings(proposed), _normalized_strings(actual))
    attribution = _read_graph(repository_url, PROVENANCE_GRAPH)
    activities = set(attribution.subjects(RDF.type, PROV.Activity))
    assert len(activities) == 1, "Exactly one durable change record must describe this commit."
    activity = next(iter(activities))
    assert set(attribution.objects(activity, PROV.wasAssociatedWith)) == {actor}
    assert (activity, PROV.generated, URIRef(graph_iri)) in attribution

    # Proposed attribution vocabulary extends the existing PROV activity.
    assert set(attribution.objects(activity, CHANGE.affectedResource)) == {
        account, user, membership,
    }, "IT-64R5S1 requires the change record to identify every affected customer resource."
    operations = list(attribution.objects(activity, CHANGE.operation))
    assert len(operations) == 1 and str(operations[0]) == "replace", (
        "The change record must identify this whole-graph commit's replace operation."
    )
    versions = list(attribution.objects(activity, CHANGE.shapeVersion))
    assert len(versions) == 1 and str(versions[0]) == "it64-r5-s1-test-v1", (
        "The change record must identify the shape version installed by the fixture."
    )
    times = list(attribution.objects(activity, PROV.startedAtTime))
    assert len(times) == 1 and isinstance(times[0], Literal) and times[0].datatype == XSD.dateTime
    timestamp = times[0].toPython()
    assert isinstance(timestamp, datetime) and timestamp.utcoffset() is not None
    assert started - timedelta(seconds=5) <= timestamp <= finished + timedelta(seconds=5), (
        "The record must include the time of this change."
    )
    # A fresh read must retrieve the same durable record, not an in-memory result.
    reread = _read_graph(repository_url, PROVENANCE_GRAPH)
    assert isomorphic(_normalized_strings(attribution), _normalized_strings(reread))
