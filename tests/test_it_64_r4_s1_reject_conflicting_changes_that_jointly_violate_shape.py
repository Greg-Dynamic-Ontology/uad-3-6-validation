"""IT-64R4S1: reject concurrent changes that jointly violate a shape."""

import os
from pathlib import Path
from uuid import uuid4
from urllib.parse import parse_qs, urlsplit
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from urllib.error import HTTPError

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
    sh:property [ sh:path customer:label ; sh:maxCount 1 ; sh:datatype xsd:string ] ;
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
            shapes_version="it64-r4-s1-test-v1",
            data_graph_iris=("urn:uad:test:it64:r4:s1:customer",),
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

def test_it_64_r4_s1_reject_conflicting_changes_that_jointly_violate_shape(request):
    # An incremental API is necessary: replacing a complete graph can silently
    # overwrite another writer and cannot demonstrate this additive conflict.
    assert callable(getattr(CustomerRdfStore, "apply_change", None)), (
        "IT-64R4S1 requires apply_change(additions=..., removals=..., actor_id=...) "
        "to apply an incremental customer RDF change in one validated transaction."
    )
    repository_url = request.getfixturevalue("customer_test_repository_url")
    graph_iri = "urn:uad:test:it64:r4:s1:customer"
    customer = Namespace("urn:uad:customer:")
    account = URIRef("urn:uad:test:account:it64-r4-s1")
    membership = URIRef("urn:uad:test:membership:it64-r4-s1")
    user = URIRef("urn:uad:test:user:it64-r4-s1")
    initial = Graph()
    initial.add((account, RDF.type, customer.CustomerAccount))
    initial.add((account, customer.name, Literal("Concurrent account", datatype=XSD.string)))
    initial.add((account, customer.createdAt, Literal(
        "2026-11-05T12:00:00Z", datatype=XSD.dateTime,
    )))
    initial.add((user, RDF.type, customer.User))
    initial.add((membership, RDF.type, customer.Membership))
    initial.add((membership, customer.account, account))
    initial.add((membership, customer.user, user))
    initial.add((membership, customer.role, customer.Owner))
    baseline = CustomerRdfStore(repository_url, graph_iri)
    baseline.commit(initial, actor_id="urn:uad:test:system:it64-r4-s1")

    changes = []
    for label in ("Alpha", "Beta"):
        addition = Graph()
        addition.add((account, customer.label, Literal(label, datatype=XSD.string)))
        changes.append(addition)

    # Establish with real GraphDB commits that each change conforms alone.
    for index, addition in enumerate(changes):
        baseline.apply_change(
            additions=addition, removals=Graph(),
            actor_id=f"urn:uad:test:actor:it64-r4-s1:{index}",
        )
        assert isomorphic(
            _normalized_strings(initial + addition), _normalized_strings(baseline.retrieve()),
        ), "Prerequisite failed: an individually conforming addition did not persist."
        baseline.commit(initial, actor_id="urn:uad:test:system:it64-r4-s1")
    assert isomorphic(_normalized_strings(initial), _normalized_strings(baseline.retrieve()))

    # Both begin against the unchanged baseline, stage their additions, and
    # reach COMMIT before either may send it. No network operation is mocked.
    begun = Barrier(2, timeout=40)
    staged = Barrier(2, timeout=40)

    class ConcurrentStore(CustomerRdfStore):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.transaction_starts = 0
            self.commit_attempts = 0

        def _request(self, method, url, **kwargs):
            parsed = urlsplit(url)
            action = parse_qs(parsed.query).get("action", [None])[0]
            if method == "PUT" and action == "COMMIT":
                self.commit_attempts += 1
                staged.wait()
            response = super()._request(method, url, **kwargs)
            if method == "POST" and parsed.path.endswith("/transactions"):
                self.transaction_starts += 1
                begun.wait()
            return response

    writers = [ConcurrentStore(repository_url, graph_iri) for _ in changes]

    def attempt(index):
        try:
            writers[index].apply_change(
                additions=changes[index], removals=Graph(),
                actor_id=f"urn:uad:test:actor:it64-r4-s1:{index}",
            )
            return None
        except Exception as error:
            return error

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(attempt, index) for index in range(2)]
        outcomes = [future.result(timeout=100) for future in futures]

    try:
        assert all(writer.transaction_starts == 1 for writer in writers), (
            "Each change must use one transaction; silent retries change this scenario."
        )
        assert all(writer.commit_attempts == 1 for writer in writers), (
            "Both transactions must reach their commit attempt. Barrier timeouts "
            "or earlier failures are test/setup failures, not verified SHACL rejection. "
            f"Outcomes: {[type(error).__name__ for error in outcomes]}"
        )
        successes = [index for index, error in enumerate(outcomes) if error is None]
        assert len(successes) < 2, (
            "IT-64R4S1: both conflicting additions were reported committed even "
            "though customer:label permits at most one value."
        )
        sh = Namespace("http://www.w3.org/ns/shacl#")
        for error in outcomes:
            if error is None:
                continue
            report = getattr(error, "validation_report", None)
            is_validation = isinstance(report, Graph) and any(
                (node, sh.conforms, Literal(False)) in report
                for node in report.subjects(RDF.type, sh.ValidationReport)
            )
            is_conflict = isinstance(error, HTTPError) and error.code == 409
            assert is_validation or is_conflict, (
                "Every rejected transaction must surface a SHACL validation or "
                f"transaction-conflict failure, not {type(error).__name__}."
            )

        expected = Graph()
        for triple in initial:
            expected.add(triple)
        for index in successes:
            for triple in changes[index]:
                expected.add(triple)
        actual = CustomerRdfStore(repository_url, graph_iri).retrieve()
        assert len(list(actual.objects(account, customer.label))) <= 1, (
            "The resulting graph must satisfy the active label maxCount constraint."
        )
        assert isomorphic(_normalized_strings(expected), _normalized_strings(actual)), (
            "Persisted RDF must contain exactly the successful changes and the "
            "unchanged conforming baseline; rejected additions must be absent."
        )
    finally:
        for error in outcomes:
            close = getattr(error, "close", None)
            if callable(close):
                close()
