"""IT-65R2S1: create a solo or company account and reload it from GraphDB."""

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
            shapes_version="it65-r2-s1-test-v1",
            data_graph_iris=("urn:uad:test:it65:r2:s1:customer",),
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


@pytest.mark.parametrize("account_type", ["solo", "company"])
def test_it_65_r2_s1_create_customer_account(request, account_type):
    parameters = signature(accounts.create_customer_account).parameters
    missing = {"account_type", "account_information"} - set(parameters)
    assert not missing, (
        "IT-65R2S1 requires create_customer_account to accept account_type and "
        f"account_information; missing: {', '.join(sorted(missing))}."
    )
    repository_type = getattr(rdf_adapter, "GraphDBCustomerAccountRepository", None)
    assert callable(repository_type), (
        "IT-65R2S1 requires GraphDBCustomerAccountRepository(repository_url=..., "
        "graph_iri=...) with add(account) and get(customer_account_id)."
    )
    repository_url = request.getfixturevalue("customer_test_repository_url")
    graph_iri = "urn:uad:test:it65:r2:s1:customer"
    owner = SimpleNamespace(
        human_user_id="urn:uad:test:user:it65-r2-s1",
        workos_user_id="user_it65_r2_s1_owner",
        internal_phone_number="19999999999",
        phone_number_verified=True,
        eligible_to_create_customer_account=True,
    )
    information = {
        "display_name": f"Test {account_type} account",
        "primary_contact_name": "Test Account Owner",
        "primary_contact_email": "owner@example.test",
    }
    if account_type == "company":
        information["company_name"] = "Test Appraisal Company"
    history = AuditHistory()
    repository = repository_type(repository_url=repository_url, graph_iri=graph_iri)
    created = accounts.create_customer_account(
        person=owner,
        id_generator=accounts.UniqueCustomerAccountIdGenerator(),
        account_repository=repository,
        audit_history=history,
        account_type=account_type,
        account_information=information,
    )
    identifier = created.customer_account_id
    assert isinstance(identifier, str) and identifier.strip()
    assert identifier not in {owner.human_user_id, owner.workos_user_id}

    def check_account(account):
        assert account.customer_account_id == identifier
        assert account.account_type == account_type
        assert account.status == "active"
        for field_name, value in information.items():
            assert getattr(account, field_name, None) == value, (
                f"The returned account must expose its stored {field_name} for display."
            )
        assert len(account.memberships) == 1
        membership = account.memberships[0]
        assert membership.human_user_id == owner.human_user_id
        assert membership.customer_account_id == identifier
        assert membership.active is True
        assert membership.role == accounts.CustomerAccountRole.OWNER
        authorization = authorize_customer_activity(
            membership, identifier,
            CustomerAccountActivity.MANAGE_MEMBERSHIP_AND_ACCOUNT_CLOSURE,
        )
        assert authorization.result == AuthorizationResult.ALLOWED

    check_account(created)
    # A fresh repository must reconstruct the aggregate from durable GraphDB
    # data, not from the object returned by creation or an instance-local cache.
    del repository
    later_repository = repository_type(repository_url=repository_url, graph_iri=graph_iri)
    reloaded = later_repository.get(identifier)
    check_account(reloaded)

    customer = Namespace("urn:uad:customer:")
    persisted = _read_graph(repository_url, graph_iri)
    assert set(persisted.subjects(RDF.type, customer.CustomerAccount)) == {URIRef(identifier)}
    memberships = set(persisted.subjects(RDF.type, customer.Membership))
    assert len(memberships) == 1, "Creation must persist exactly one owner membership."
    membership_node = next(iter(memberships))
    assert (membership_node, customer.account, URIRef(identifier)) in persisted
    assert (membership_node, customer.user, URIRef(owner.human_user_id)) in persisted
    assert (membership_node, customer.role, customer.Owner) in persisted
    attribution = _read_graph(repository_url, PROVENANCE_GRAPH)
    assert any(
        (activity, PROV.wasAssociatedWith, URIRef(owner.human_user_id)) in attribution
        and (activity, PROV.generated, URIRef(graph_iri)) in attribution
        for activity in attribution.subjects(RDF.type, PROV.Activity)
    ), "The durable account creation must be attributable to the acting UAD user."
