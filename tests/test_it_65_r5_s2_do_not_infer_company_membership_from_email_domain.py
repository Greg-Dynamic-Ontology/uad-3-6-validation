"""IT-65R5S2: a matching email domain does not authorize account access."""

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
            shapes_version="it65-r5-s2-test-v1",
            data_graph_iris=("urn:uad:test:it65:r5:s2:customer",),
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


@pytest.mark.parametrize("membership_state", ["absent", "inactive"])
def test_it_65_r5_s2_do_not_infer_company_membership_from_email_domain(
    request, membership_state,
):
    view = getattr(accounts, "view_customer_account", None)
    assert callable(view), "IT-65R5S2 requires the account-view service."
    repository_url = request.getfixturevalue("customer_test_repository_url")
    graph_iri = "urn:uad:test:it65:r5:s2:customer"
    owner_id = "urn:uad:test:user:it65-r5-s2-owner"
    # Authentication and the identity-to-UAD-ID link are supplied prerequisites.
    signed_in_user = SimpleNamespace(
        human_user_id="urn:uad:test:user:it65-r5-s2-requester",
        email="employee@company.example.test",
    )
    company_email = "owner@company.example.test"
    assert signed_in_user.email.split("@")[1] == company_email.split("@")[1]
    repository = rdf_adapter.GraphDBCustomerAccountRepository(
        repository_url=repository_url, graph_iri=graph_iri,
    )

    def create(user_id, account_type, email):
        information = {
            "display_name": "Company" if account_type == "company" else "Personal",
            "primary_contact_name": "Contact",
            "primary_contact_email": email,
        }
        if account_type == "company":
            information["company_name"] = "Matching Domain Company"
            information["company_website"] = "https://company.example.test"
        return accounts.create_customer_account(
            person=SimpleNamespace(
                human_user_id=user_id, workos_user_id="workos_" + account_type,
                internal_phone_number="19999999999", phone_number_verified=True,
                eligible_to_create_customer_account=True,
            ),
            id_generator=accounts.UniqueCustomerAccountIdGenerator(),
            account_repository=repository, audit_history=AuditHistory(),
            account_type=account_type, account_information=information,
        )

    company = create(owner_id, "company", company_email)
    # The requester's matching address is also present in persisted account
    # information, but owning this solo account grants no company membership.
    personal = create(signed_in_user.human_user_id, "solo", signed_in_user.email)
    customer = Namespace("urn:uad:customer:")
    additions = Graph()
    # Explicit test identity metadata makes the matching email available in
    # RDF. This is fixture metadata, not a claim about WorkOS synchronization.
    additions.add((
        URIRef(signed_in_user.human_user_id),
        URIRef("https://schema.org/email"),
        Literal(signed_in_user.email, datatype=XSD.string),
    ))
    if membership_state == "inactive":
        node = URIRef("urn:uad:test:membership:it65-r5-s2-inactive")
        additions.add((node, RDF.type, customer.Membership))
        additions.add((node, customer.account, URIRef(company.customer_account_id)))
        additions.add((node, customer.user, URIRef(signed_in_user.human_user_id)))
        additions.add((node, customer.humanUserId, Literal(signed_in_user.human_user_id, datatype=XSD.string)))
        additions.add((node, customer.role, customer.Reviewer))
        additions.add((node, customer.active, Literal(False)))
    rdf_adapter.CustomerRdfStore(
        repository_url=repository_url, graph_iri=graph_iri,
    ).apply_change(additions=additions, removals=Graph(), actor_id=owner_id)

    fresh = rdf_adapter.GraphDBCustomerAccountRepository(
        repository_url=repository_url, graph_iri=graph_iri,
    )
    stored = fresh.get(company.customer_account_id)
    assert not any(
        member.active and member.human_user_id == signed_in_user.human_user_id
        for member in stored.memberships
    )
    # Positive controls: the owner can view the company and the requester can
    # view their personal account. An implementation denying everyone fails.
    assert view(
        human_user_id=owner_id, customer_account_id=company.customer_account_id,
        account_repository=fresh,
    ).account.customer_account_id == company.customer_account_id
    assert view(
        human_user_id=signed_in_user.human_user_id,
        customer_account_id=personal.customer_account_id,
        account_repository=fresh,
    ).account.customer_account_id == personal.customer_account_id
    before = _read_graph(repository_url, graph_iri)
    attribution_before = _read_graph(repository_url, PROVENANCE_GRAPH)

    # Access uses the authenticated stable UAD ID. There is deliberately no
    # email-based authorization parameter in the application service contract.
    with pytest.raises(PermissionError):
        view(
            human_user_id=signed_in_user.human_user_id,
            customer_account_id=company.customer_account_id,
            account_repository=fresh,
        )
    visible = accounts.list_customer_accounts(
        human_user_id=signed_in_user.human_user_id, account_repository=fresh,
    )
    assert {item.customer_account_id for item in visible} == {personal.customer_account_id}
    assert isomorphic(
        _normalized_strings(before),
        _normalized_strings(_read_graph(repository_url, graph_iri)),
    ), "Access must not infer, create, or reactivate company membership from an email domain."
    assert isomorphic(
        _normalized_strings(attribution_before),
        _normalized_strings(_read_graph(repository_url, PROVENANCE_GRAPH)),
    ), "A denied access request must not produce committed-change attribution."
