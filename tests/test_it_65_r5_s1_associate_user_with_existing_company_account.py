"""IT-65R5S1: durably grant an explicit role in an existing company account."""

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
            shapes_version="it65-r5-s1-test-v1",
            data_graph_iris=("urn:uad:test:it65:r5:s1:customer",),
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


import app.services.account_memberships as memberships
from app.services.account_authorization import (
    AuthorizationResult, CustomerAccountActivity, authorize_customer_activity,
)

@pytest.mark.parametrize("role", list(accounts.CustomerAccountRole), ids=lambda role: role.value)
def test_it_65_r5_s1_associate_user_with_existing_company_account(request, role):
    grant = getattr(memberships, "grant_customer_account_membership", None)
    assert callable(grant), (
        "IT-65R5S1 requires grant_customer_account_membership("
        "actor_id=..., human_user_id=..., customer_account_id=..., role=..., "
        "account_repository=..., audit_history=...) to persist an active membership."
    )
    repository_url = request.getfixturevalue("customer_test_repository_url")
    graph_iri = "urn:uad:test:it65:r5:s1:customer"
    actor_id = "urn:uad:test:user:it65-r5-s1-owner"
    target_user = "urn:uad:test:user:it65-r5-s1-authenticated"
    # Authentication and linking to this stable UAD ID are prerequisites;
    # this integration test does not contact WorkOS or implement invitations.
    repository = rdf_adapter.GraphDBCustomerAccountRepository(
        repository_url=repository_url, graph_iri=graph_iri,
    )
    created = accounts.create_customer_account(
        person=SimpleNamespace(
            human_user_id=actor_id, workos_user_id="user_it65_r5_s1_owner",
            internal_phone_number="19999999999", phone_number_verified=True,
            eligible_to_create_customer_account=True,
        ),
        id_generator=accounts.UniqueCustomerAccountIdGenerator(),
        account_repository=repository, audit_history=AuditHistory(),
        account_type="company",
        account_information={
            "display_name": "Existing company account",
            "company_name": "Existing Company",
            "primary_contact_name": "Owner Contact",
            "primary_contact_email": "owner@example.test",
        },
    )
    account_id = created.customer_account_id
    customer = Namespace("urn:uad:customer:")
    before = _read_graph(repository_url, graph_iri)
    account_ids_before = set(before.subjects(RDF.type, customer.CustomerAccount))
    assert account_ids_before == {URIRef(account_id)}
    assert repository.list_for_user(target_user) == ()
    stored_before = repository.get(account_id)
    assert stored_before.status == "active"
    assert stored_before.account_type == "company"

    grant(
        actor_id=actor_id, human_user_id=target_user,
        customer_account_id=account_id, role=role,
        account_repository=repository, audit_history=AuditHistory(),
    )

    fresh = rdf_adapter.GraphDBCustomerAccountRepository(
        repository_url=repository_url, graph_iri=graph_iri,
    )
    stored_after = fresh.get(account_id)
    matches = [
        member for member in stored_after.memberships
        if member.human_user_id == target_user
    ]
    assert len(matches) == 1, "Granting one role must create exactly one target membership."
    membership = matches[0]
    assert membership.customer_account_id == account_id
    assert membership.active is True
    assert membership.role == role
    assert set(stored_before.memberships) <= set(stored_after.memberships)
    assert len(stored_after.memberships) == len(stored_before.memberships) + 1

    after = _read_graph(repository_url, graph_iri)
    assert set(after.subjects(RDF.type, customer.CustomerAccount)) == account_ids_before, (
        "Associating a user must not create another customer account."
    )
    # The account's own information and all pre-existing RDF must survive.
    def account_triples(graph):
        result = Graph()
        for triple in graph.triples((URIRef(account_id), None, None)):
            result.add(triple)
        return _normalized_strings(result)

    assert isomorphic(account_triples(before), account_triples(after))
    assert set(_normalized_strings(before)) <= set(_normalized_strings(after)), (
        "A membership grant must preserve existing customer RDF."
    )
    visible = fresh.list_for_user(target_user)
    assert [account.customer_account_id for account in visible] == [account_id]

    # Exercise public authorization decisions for each role's primary activity.
    # Check the complete matrix, not merely the one permitted activity.
    activities = {
        accounts.CustomerAccountRole.OWNER:
            CustomerAccountActivity.MANAGE_MEMBERSHIP_AND_ACCOUNT_CLOSURE,
        accounts.CustomerAccountRole.BILLING_ADMINISTRATOR:
            CustomerAccountActivity.PURCHASE_CREDITS_AND_VIEW_FINANCIAL_HISTORY,
        accounts.CustomerAccountRole.VALIDATOR:
            CustomerAccountActivity.SUBMIT_REPORTS_AND_MANAGE_VALIDATION_CYCLES,
        accounts.CustomerAccountRole.REVIEWER:
            CustomerAccountActivity.VIEW_REPORTS_FINDINGS_AND_CYCLE_HISTORIES,
    }
    for activity_role, activity in activities.items():
        decision = authorize_customer_activity(membership, account_id, activity)
        expected = (
            AuthorizationResult.ALLOWED if activity_role == role
            else AuthorizationResult.DENIED
        )
        assert decision.result == expected, (
            f"{role.value} must receive only its granted permissions: {activity.value}."
        )
        unrelated = authorize_customer_activity(
            membership, "urn:uad:test:account:it65-r5-s1-unrelated", activity,
        )
        assert unrelated.result == AuthorizationResult.DENIED, (
            "The granted role must apply only within the selected company account."
        )
