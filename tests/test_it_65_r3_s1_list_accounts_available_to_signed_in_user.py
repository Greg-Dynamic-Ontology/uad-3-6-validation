"""IT-65R3S1: list only accounts available to the signed-in user."""

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
            shapes_version="it65-r3-s1-test-v1",
            data_graph_iris=("urn:uad:test:it65:r3:s1:customer",),
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


def test_it_65_r3_s1_list_accounts_available_to_signed_in_user(request):
    list_accounts = getattr(accounts, "list_customer_accounts", None)
    assert callable(list_accounts), (
        "IT-65R3S1 requires list_customer_accounts(human_user_id=..., "
        "account_repository=...) returning account summaries with the user's role."
    )
    repository_url = request.getfixturevalue("customer_test_repository_url")
    graph_iri = "urn:uad:test:it65:r3:s1:customer"
    signed_in_user = "urn:uad:test:user:it65-r3-s1-signed-in"
    another_user = "urn:uad:test:user:it65-r3-s1-other"
    customer = Namespace("urn:uad:customer:")
    repository = rdf_adapter.GraphDBCustomerAccountRepository(
        repository_url=repository_url, graph_iri=graph_iri,
    )

    def create(owner_id, display_name, account_type):
        person = SimpleNamespace(
            human_user_id=owner_id, workos_user_id="user_" + owner_id.rsplit(":", 1)[-1],
            internal_phone_number="19999999999", phone_number_verified=True,
            eligible_to_create_customer_account=True,
        )
        information = {
            "display_name": display_name,
            "primary_contact_name": "Test Owner",
            "primary_contact_email": "owner@example.test",
        }
        if account_type == "company":
            information["company_name"] = display_name + " Company"
        return accounts.create_customer_account(
            person=person, id_generator=accounts.UniqueCustomerAccountIdGenerator(),
            account_repository=repository, audit_history=AuditHistory(),
            account_type=account_type, account_information=information,
        )

    owned = create(signed_in_user, "Owned solo account", "solo")
    shared = create(another_user, "Shared company account", "company")
    inactive = create(another_user, "Inactive membership account", "solo")
    unrelated = create(another_user, "Unrelated company account", "company")

    # Seed one active validator membership and one inactive reviewer membership
    # without invoking listing logic. Ownership remains with the original owner.
    memberships = Graph()
    for account, role, active, suffix in (
        (shared, customer.Validator, True, "active"),
        (inactive, customer.Reviewer, False, "inactive"),
    ):
        node = URIRef(f"urn:uad:test:membership:it65-r3-s1-{suffix}")
        memberships.add((node, RDF.type, customer.Membership))
        memberships.add((node, customer.account, URIRef(account.customer_account_id)))
        memberships.add((node, customer.user, URIRef(signed_in_user)))
        memberships.add((node, customer.humanUserId, Literal(signed_in_user, datatype=XSD.string)))
        memberships.add((node, customer.role, role))
        memberships.add((node, customer.active, Literal(active)))
    CustomerRdfStore(repository_url, graph_iri).apply_change(
        additions=memberships, removals=Graph(), actor_id=another_user,
    )
    data_before = _read_graph(repository_url, graph_iri)
    attribution_before = _read_graph(repository_url, PROVENANCE_GRAPH)

    # Use a new repository instance so membership visibility must come from
    # GraphDB, not the account objects returned during fixture creation.
    fresh = rdf_adapter.GraphDBCustomerAccountRepository(
        repository_url=repository_url, graph_iri=graph_iri,
    )
    entries = list(list_accounts(human_user_id=signed_in_user, account_repository=fresh))
    expected = {
        owned.customer_account_id: (owned, accounts.CustomerAccountRole.OWNER),
        shared.customer_account_id: (shared, accounts.CustomerAccountRole.VALIDATOR),
    }
    assert len(entries) == 2, "List each authorized account once; exclude unrelated and inactive memberships."
    assert {entry.customer_account_id for entry in entries} == set(expected)
    for entry in entries:
        account, role = expected[entry.customer_account_id]
        assert entry.display_name == account.display_name
        assert entry.account_type == account.account_type
        assert entry.status == account.status
        assert entry.role == role, "Report this user's role, not another member's owner role."
    assert inactive.customer_account_id not in {entry.customer_account_id for entry in entries}
    assert unrelated.customer_account_id not in {entry.customer_account_id for entry in entries}
    assert list(list_accounts(
        human_user_id="urn:uad:test:user:it65-r3-s1-no-memberships", account_repository=fresh,
    )) == []
    assert isomorphic(_normalized_strings(data_before), _normalized_strings(_read_graph(repository_url, graph_iri)))
    assert isomorphic(
        _normalized_strings(attribution_before),
        _normalized_strings(_read_graph(repository_url, PROVENANCE_GRAPH)),
    ), "Listing accounts must not modify customer data or create change records."
