"""IT-65R6S1: close an obligation-free account durably and block new activity."""

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
            shapes_version="it65-r6-s1-test-v1",
            data_graph_iris=("urn:uad:test:it65:r6:s1:customer",),
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


from datetime import datetime, timezone

import app.services.customer_account_lifecycle as lifecycle
import app.services.account_memberships as memberships
from app.services.account_authorization import (
    AuthorizationResult, CustomerAccountActivity, request_customer_account_activity,
)


class ClearObligations:
    """Controlled obligations boundary; no payment provider is contacted.

    This test verifies that closure consults the boundary for the correct
    account. It does not establish production billing/credit reconciliation.
    """

    def __init__(self):
        self.requests = []

    def get_account_obligations(self, customer_account_id):
        self.requests.append(customer_account_id)
        return SimpleNamespace(
            remaining_validation_credits=0,
            validation_work_in_progress=0,
            pending_purchases=0,
            unresolved_payment_obligations=0,
        )


def test_it_65_r6_s1_close_account_with_no_outstanding_obligations(request):
    close_account = getattr(lifecycle, "request_customer_account_closure", None)
    assert callable(close_account), (
        "IT-65R6S1 requires request_customer_account_closure("
        "actor_id=..., customer_account_id=..., confirmed=..., "
        "account_repository=..., obligation_repository=..., audit_history=...) "
        "to close the persisted account after explicit owner confirmation."
    )
    repository_url = request.getfixturevalue("customer_test_repository_url")
    graph_iri = "urn:uad:test:it65:r6:s1:customer"
    owner_id = "urn:uad:test:user:it65-r6-s1-owner"
    operator_id = "urn:uad:test:user:it65-r6-s1-operator"
    repository = rdf_adapter.GraphDBCustomerAccountRepository(
        repository_url=repository_url, graph_iri=graph_iri,
    )

    def create(name):
        return accounts.create_customer_account(
            person=SimpleNamespace(
                human_user_id=owner_id, workos_user_id="user_it65_r6_s1_owner",
                internal_phone_number="19999999999", phone_number_verified=True,
                eligible_to_create_customer_account=True,
            ),
            id_generator=accounts.UniqueCustomerAccountIdGenerator(),
            account_repository=repository, audit_history=AuditHistory(),
            account_type="company",
            account_information={
                "display_name": name, "company_name": name,
                "primary_contact_name": "Owner Contact",
                "primary_contact_email": "owner@example.test",
            },
        )

    target = create("Account to close")
    other = create("Account to preserve")
    account_id = target.customer_account_id
    for account in (target, other):
        for role in (
            accounts.CustomerAccountRole.BILLING_ADMINISTRATOR,
            accounts.CustomerAccountRole.VALIDATOR,
        ):
            memberships.grant_customer_account_membership(
                actor_id=owner_id, human_user_id=operator_id,
                customer_account_id=account.customer_account_id, role=role,
                account_repository=repository, audit_history=AuditHistory(),
            )
    customer = Namespace("urn:uad:customer:")
    fixture = Namespace("urn:uad:test:it65:r6:s1:history:")
    history_rdf = Graph()
    for name, kind in (
        ("spent-credits", fixture.CreditLot),
        ("completed-report", fixture.ValidationReport),
        ("completed-cycle", fixture.ValidationCycle),
        ("settled-payment", fixture.Payment),
    ):
        history_rdf.add((fixture[name], RDF.type, kind))
        history_rdf.add((fixture[name], customer.account, URIRef(account_id)))
        history_rdf.add((fixture[name], fixture.status, Literal("completed")))
    history_rdf.add((fixture["spent-credits"], fixture.remainingQuantity, Literal(0)))
    rdf_adapter.CustomerRdfStore(
        repository_url=repository_url, graph_iri=graph_iri,
    ).apply_change(additions=history_rdf, removals=Graph(), actor_id=owner_id)

    before_account = repository.get(account_id)
    before_other = repository.get(other.customer_account_id)
    operations = (
        (accounts.CustomerAccountRole.BILLING_ADMINISTRATOR,
         CustomerAccountActivity.PURCHASE_VALIDATION_CREDITS),
        (accounts.CustomerAccountRole.VALIDATOR,
         CustomerAccountActivity.SUBMIT_REPORTS_AND_MANAGE_VALIDATION_CYCLES),
    )
    # Positive controls prevent a blanket deny-all implementation from passing.
    for role, activity in operations:
        member = next(
            m for m in before_account.memberships
            if m.human_user_id == operator_id and m.role == role
        )
        assert request_customer_account_activity(
            membership=member, customer_account=before_account,
            activity=activity, audit_history=AuditHistory(),
        ).result == AuthorizationResult.ALLOWED

    before = _read_graph(repository_url, graph_iri)
    records_before = _read_graph(repository_url, PROVENANCE_GRAPH)
    prior_activities = set(records_before.subjects(RDF.type, PROV.Activity))
    obligations = ClearObligations()
    started = datetime.now(timezone.utc)
    close_account(
        actor_id=owner_id, customer_account_id=account_id, confirmed=True,
        account_repository=repository, obligation_repository=obligations,
        audit_history=AuditHistory(),
    )
    finished = datetime.now(timezone.utc)
    assert obligations.requests and set(obligations.requests) == {account_id}

    fresh = rdf_adapter.GraphDBCustomerAccountRepository(
        repository_url=repository_url, graph_iri=graph_iri,
    )
    closed = fresh.get(account_id)
    assert closed.status == "closed"
    assert closed.customer_account_id == account_id
    assert closed.memberships == before_account.memberships
    assert fresh.get(other.customer_account_id) == before_other

    after = _read_graph(repository_url, graph_iri)
    # Every previous triple except the lifecycle status must survive, including
    # histories, identities and memberships in both accounts.
    for triple in _normalized_strings(before):
        if triple[:2] != (URIRef(account_id), customer.status):
            assert triple in _normalized_strings(after), f"Closure removed stored RDF: {triple}"
    assert list(after.objects(URIRef(account_id), customer.status)) == [
        Literal("closed", datatype=XSD.string)
    ] or {
        str(value) for value in after.objects(URIRef(account_id), customer.status)
    } == {"closed"}
    assert set(after.subjects(RDF.type, customer.CustomerAccount)) == set(
        before.subjects(RDF.type, customer.CustomerAccount)
    )
    records_after = _read_graph(repository_url, PROVENANCE_GRAPH)
    new_activities = set(records_after.subjects(RDF.type, PROV.Activity)) - prior_activities
    closure_records = [
        record for record in new_activities
        if (record, CHANGE.affectedResource, URIRef(account_id)) in records_after
        and (record, PROV.wasAssociatedWith, URIRef(owner_id)) in records_after
    ]
    assert closure_records, "Closure must durably identify the closing owner and account."
    for record in closure_records:
        times = list(records_after.objects(record, PROV.startedAtTime))
        assert len(times) == 1 and times[0].datatype == XSD.dateTime
        timestamp = times[0].toPython()
        assert isinstance(timestamp, datetime) and timestamp.utcoffset() is not None
        assert started <= timestamp <= finished

    for role, activity in operations:
        member = next(
            m for m in closed.memberships
            if m.human_user_id == operator_id and m.role == role
        )
        assert request_customer_account_activity(
            membership=member, customer_account=closed,
            activity=activity, audit_history=AuditHistory(),
        ).result == AuthorizationResult.DENIED, (
            f"Closed accounts must reject {activity.value} despite an active role."
        )
        other_member = next(
            m for m in before_other.memberships
            if m.human_user_id == operator_id and m.role == role
        )
        assert request_customer_account_activity(
            membership=other_member, customer_account=fresh.get(other.customer_account_id),
            activity=activity, audit_history=AuditHistory(),
        ).result == AuthorizationResult.ALLOWED
