"""IT-65R2S5: retry account creation without duplicating persisted resources."""

import os
from pathlib import Path
from inspect import signature
from types import SimpleNamespace
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
            shapes_version="it65-r2-s5-test-v1",
            data_graph_iris=("urn:uad:test:it65:r2:s5:customer",),
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


@pytest.mark.parametrize("account_type", ["solo", "company"])
def test_it_65_r2_s5_avoid_duplicate_accounts_when_creation_is_retried(request, account_type):
    assert "request_id" in signature(accounts.create_customer_account).parameters, (
        "IT-65R2S5 requires create_customer_account(..., request_id=...) to "
        "recognize a previously completed creation request across sessions."
    )
    repository_url = request.getfixturevalue("customer_test_repository_url")
    graph_iri = "urn:uad:test:it65:r2:s5:customer"
    owner = SimpleNamespace(
        human_user_id="urn:uad:test:user:it65-r2-s5",
        workos_user_id="user_it65_r2_s5_owner",
        internal_phone_number="19999999999",
        phone_number_verified=True,
        eligible_to_create_customer_account=True,
    )
    information = {
        "display_name": "Retry-safe customer account",
        "primary_contact_name": "Test Owner",
        "primary_contact_email": "owner@example.test",
    }
    if account_type == "company":
        information["company_name"] = "Test Appraisal Company"
    request_id = str(uuid4())
    first_ids = CountingAccountIds()
    first_audit = AuditHistory()
    first_repository = rdf_adapter.GraphDBCustomerAccountRepository(
        repository_url=repository_url, graph_iri=graph_iri,
    )
    first = accounts.create_customer_account(
        person=owner, id_generator=first_ids,
        account_repository=first_repository, audit_history=first_audit,
        account_type=account_type, account_information=dict(information),
        request_id=request_id,
    )
    assert first_ids.calls == 1
    assert first.customer_account_id
    assert len(first.memberships) == 1
    customer = Namespace("urn:uad:customer:")
    data_before = _read_graph(repository_url, graph_iri)
    records_before = _read_graph(repository_url, PROVENANCE_GRAPH)
    assert set(data_before.subjects(RDF.type, customer.CustomerAccount)) == {
        URIRef(first.customer_account_id),
    }
    assert len(set(data_before.subjects(RDF.type, customer.Membership))) == 1
    assert len(set(records_before.subjects(RDF.type, PROV.Activity))) == 1
    del first_repository

    # New repository, ID generator, and audit boundary model a later request.
    # Repeat twice to catch logic that only suppresses a single duplicate.
    for _ in range(2):
        retry_ids = CountingAccountIds()
        retry_audit = AuditHistory()
        retry_repository = rdf_adapter.GraphDBCustomerAccountRepository(
            repository_url=repository_url, graph_iri=graph_iri,
        )
        retried = accounts.create_customer_account(
            person=owner, id_generator=retry_ids,
            account_repository=retry_repository, audit_history=retry_audit,
            account_type=account_type, account_information=dict(information),
            request_id=request_id,
        )
        assert retried == first, "Return the previously created aggregate, including its original identity and time."
        assert retry_ids.calls == 0, "A completed request must not issue another account ID."
        assert retry_repository.get(first.customer_account_id) == first
        assert not [
            event for event in retry_audit.events
            if event.get("event_type") in {"customer_account_created", "owner_assigned"}
        ], "Do not report duplicate account creation or owner assignment."
        assert isomorphic(
            _normalized_strings(data_before), _normalized_strings(_read_graph(repository_url, graph_iri)),
        ), "A retry must not change the persisted account or add another membership."
        assert isomorphic(
            _normalized_strings(records_before), _normalized_strings(_read_graph(repository_url, PROVENANCE_GRAPH)),
        ), "A retry must not commit a duplicate durable creation record."

    # Identical information with a different request ID is a distinct request;
    # matching on owner or display name alone is not request deduplication.
    separate = accounts.create_customer_account(
        person=owner, id_generator=CountingAccountIds(),
        account_repository=rdf_adapter.GraphDBCustomerAccountRepository(
            repository_url=repository_url, graph_iri=graph_iri,
        ),
        audit_history=AuditHistory(), account_type=account_type,
        account_information=dict(information), request_id=str(uuid4()),
    )
    assert separate.customer_account_id != first.customer_account_id
    data_after = _read_graph(repository_url, graph_iri)
    assert set(data_after.subjects(RDF.type, customer.CustomerAccount)) == {
        URIRef(first.customer_account_id), URIRef(separate.customer_account_id),
    }
    assert len(set(data_after.subjects(RDF.type, customer.Membership))) == 2
