"""IT-65R2S6: roll back incomplete account creation."""

import os
from pathlib import Path
from inspect import signature
from types import SimpleNamespace
from uuid import uuid4
from urllib.parse import urlencode, parse_qs, urlsplit
from urllib.request import Request, urlopen

import pytest

from owb_graphdb.client import GraphDBClient
from owb_graphdb.configuration import RepositoryConfiguration
from owb_graphdb.setup import setup_repository

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.compare import isomorphic
from rdflib.namespace import RDF, XSD

from app.adapters.customer_rdf_store import CustomerRdfStore
import app.adapters.customer_rdf_store as rdf_adapter
import app.services.customer_accounts as accounts
from app.services.account_authorization import (
    AuthorizationResult, CustomerAccountActivity, authorize_customer_activity,
)




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
            shapes_version="it65-r2-s6-test-v1",
            data_graph_iris=("urn:uad:test:it65:r2:s6:customer",),
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


class AuditHistory:
    """Capture service audit calls; GraphDB attribution is checked separately."""

    def __init__(self):
        self.events = []

    def record(self, **event):
        self.events.append(dict(event))


class CountingAccountIds:
    def __init__(self):
        self.calls = 0
        self.generator = accounts.UniqueCustomerAccountIdGenerator()

    def new_customer_account_id(self):
        self.calls += 1
        return self.generator.new_customer_account_id()


class InjectedAccountWriteFailure(RuntimeError):
    """Failure after successful RDF staging, before transaction commit."""


@pytest.mark.parametrize("account_type", ["solo", "company"])
def test_it_65_r2_s6_roll_back_incomplete_account_creation(
    customer_test_repository_url, monkeypatch, account_type,
):
    repository_url = customer_test_repository_url
    graph_iri = "urn:uad:test:it65:r2:s6:customer"
    customer = Namespace("urn:uad:customer:")
    owner = SimpleNamespace(
        human_user_id="urn:uad:test:user:it65-r2-s6",
        workos_user_id="user_it65_r2_s6_owner",
        internal_phone_number="19999999999",
        phone_number_verified=True,
        eligible_to_create_customer_account=True,
    )
    information = {
        "display_name": "Incomplete creation test",
        "primary_contact_name": "Test Owner",
        "primary_contact_email": "owner@example.test",
    }
    if account_type == "company":
        information["company_name"] = "Test Appraisal Company"
    request_id = str(uuid4())
    repository = rdf_adapter.GraphDBCustomerAccountRepository(
        repository_url=repository_url, graph_iri=graph_iri,
    )
    data_before = _read_graph(repository_url, graph_iri)
    attribution_before = _read_graph(repository_url, PROVENANCE_GRAPH)
    assert len(data_before) == len(attribution_before) == 0
    audit = AuditHistory()
    original_request = rdf_adapter.CustomerRdfStore._request
    staged_transaction = None
    staged_account_ids = set()
    rollback_results = []
    commit_requests = []
    injected = InjectedAccountWriteFailure("Simulated failure before account creation commit")

    def fail_after_staging(self, method, url, **kwargs):
        nonlocal staged_transaction, staged_account_ids
        query = parse_qs(urlsplit(url).query)
        action = query.get("action", [None])[0]
        if method == "PUT" and action == "COMMIT":
            commit_requests.append(url)
        response = original_request(self, method, url, **kwargs)
        if method == "DELETE" and url == staged_transaction:
            rollback_results.append(response[0])
        if (
            method == "PUT" and action == "ADD"
            and query.get("context") == [URIRef(graph_iri).n3()]
            and staged_transaction is None
        ):
            assert 200 <= response[0] < 300
            staged = Graph().parse(data=kwargs["body"].decode("utf-8"), format="nt")
            staged_account_ids = set(staged.subjects(RDF.type, customer.CustomerAccount))
            assert len(staged_account_ids) == 1
            assert len(set(staged.subjects(RDF.type, customer.Membership))) == 1
            staged_transaction = url.split("?", 1)[0]
            raise injected
        return response

    failure = None
    with monkeypatch.context() as patch:
        patch.setattr(rdf_adapter.CustomerRdfStore, "_request", fail_after_staging)
        try:
            accounts.create_customer_account(
                person=owner, id_generator=CountingAccountIds(),
                account_repository=repository, audit_history=audit,
                account_type=account_type, account_information=information,
                request_id=request_id,
            )
        except Exception as error:
            failure = error

    assert staged_transaction is not None, "The failure must occur after actual RDF staging."
    assert not commit_requests, "Incomplete creation must not attempt a transaction commit."
    assert len(rollback_results) == 1 and 200 <= rollback_results[0] < 300, (
        "GraphDB must confirm rollback of the incomplete creation transaction."
    )
    assert isomorphic(data_before, _read_graph(repository_url, graph_iri)), (
        "Neither the staged account nor its owner membership may remain committed."
    )
    assert isomorphic(attribution_before, _read_graph(repository_url, PROVENANCE_GRAPH)), (
        "Incomplete creation must not leave a durable successful-change record."
    )
    fresh = rdf_adapter.GraphDBCustomerAccountRepository(
        repository_url=repository_url, graph_iri=graph_iri,
    )
    assert fresh.find_by_creation_request(actor_id=owner.human_user_id, request_id=request_id) is None
    for identifier in staged_account_ids:
        with pytest.raises(KeyError):
            fresh.get(str(identifier))
    assert not audit.events, "Do not report account creation or owner assignment as successful."
    assert failure is not None
    assert getattr(failure, "code", None) == "account_creation_incomplete", (
        "IT-65R2S6 requires an identifiable account_creation_incomplete failure "
        f"after confirmed rollback; received {type(failure).__name__}."
    )
    assert getattr(failure, "committed", None) is False
    assert "did not complete" in str(failure).lower(), (
        "The user-facing diagnostic must explain that account creation did not complete."
    )
