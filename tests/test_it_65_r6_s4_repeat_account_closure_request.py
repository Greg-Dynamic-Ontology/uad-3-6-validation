"""IT-65R6S4: repeated closure reports already closed without another change."""

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


import app.adapters.customer_rdf_store as rdf_adapter
import app.services.customer_accounts as accounts





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
            shapes_version="it65-r6-s4-test-v1",
            data_graph_iris=("urn:uad:test:it65:r6:s4:customer",),
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


import app.services.customer_account_lifecycle as lifecycle


class ClearObligations:
    """Controlled obligations provider; no external billing service is called."""

    def get_account_obligations(self, customer_account_id):
        return SimpleNamespace(
            remaining_validation_credits=0,
            validation_work_in_progress=0,
            pending_purchases=0,
            unresolved_payment_obligations=0,
        )


def test_it_65_r6_s4_repeat_account_closure_request(request):
    close = getattr(lifecycle, "request_customer_account_closure", None)
    assert callable(close), "IT-65R6S4 requires the account-closure request service."
    repository_url = request.getfixturevalue("customer_test_repository_url")
    graph_iri = "urn:uad:test:it65:r6:s4:customer"
    actor_id = "urn:uad:test:user:it65-r6-s4-owner"
    repository = rdf_adapter.GraphDBCustomerAccountRepository(
        repository_url=repository_url, graph_iri=graph_iri,
    )
    created = accounts.create_customer_account(
        person=SimpleNamespace(
            human_user_id=actor_id, workos_user_id="user_it65_r6_s4_owner",
            internal_phone_number="19999999999", phone_number_verified=True,
            eligible_to_create_customer_account=True,
        ),
        id_generator=accounts.UniqueCustomerAccountIdGenerator(),
        account_repository=repository, audit_history=AuditHistory(),
        account_type="company",
        account_information={
            "display_name": "Already closed company", "company_name": "Existing Company",
            "primary_contact_name": "Owner Contact",
            "primary_contact_email": "owner@example.test",
        },
    )
    account_id = created.customer_account_id
    first_history = AuditHistory()
    close(
        actor_id=actor_id, customer_account_id=account_id, confirmed=True,
        account_repository=repository, obligation_repository=ClearObligations(),
        audit_history=first_history,
    )

    # Repeat from a new repository instance: persisted state must govern the
    # result, not an in-process flag left by the first closure request.
    fresh = rdf_adapter.GraphDBCustomerAccountRepository(
        repository_url=repository_url, graph_iri=graph_iri,
    )
    baseline = fresh.get(account_id)
    assert baseline.status == "closed", "Prerequisite: first closure must persist."
    assert any(
        member.active and member.role == accounts.CustomerAccountRole.OWNER
        and member.human_user_id == actor_id
        and member.customer_account_id == account_id
        for member in baseline.memberships
    ), "The repeat requester must still be the authorized owner."
    before = _read_graph(repository_url, graph_iri)
    attribution_before = _read_graph(repository_url, PROVENANCE_GRAPH)
    assert len([
        event for event in first_history.events
        if event.get("event_type") == "customer_account_closed"
    ]) == 1

    history = AuditHistory()
    # The existing lifecycle API reports business-rule outcomes as ValueError.
    # Also permit an explicit result message; neither path may write again.
    try:
        result = close(
            actor_id=actor_id, customer_account_id=account_id, confirmed=True,
            account_repository=fresh, obligation_repository=ClearObligations(),
            audit_history=history,
        )
    except ValueError as outcome:
        message = str(outcome)
    else:
        message = str(getattr(result, "message", result))
    assert "already closed" in message.casefold(), (
        "IT-65R6S4 must explicitly report that the account is already closed; "
        f"received: {message}"
    )

    observer = rdf_adapter.GraphDBCustomerAccountRepository(
        repository_url=repository_url, graph_iri=graph_iri,
    )
    assert observer.get(account_id) == baseline
    assert isomorphic(
        _normalized_strings(before),
        _normalized_strings(_read_graph(repository_url, graph_iri)),
    ), "Repeating closure must not change stored customer data."
    assert isomorphic(
        _normalized_strings(attribution_before),
        _normalized_strings(_read_graph(repository_url, PROVENANCE_GRAPH)),
    ), "Repeating closure must not create another durable closure change."
    assert not any(
        event.get("event_type") == "customer_account_closed"
        for event in history.events
    ), "Repeating closure must not report a new successful closure event."
