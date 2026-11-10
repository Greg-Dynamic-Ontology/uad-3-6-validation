"""IT-65R3S2: view persisted details in an explicit selected-account context."""

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
            shapes_version="it65-r3-s2-test-v1",
            data_graph_iris=("urn:uad:test:it65:r3:s2:customer",),
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


def test_it_65_r3_s2_view_selected_customer_account(request):
    view_account = getattr(accounts, "view_customer_account", None)
    assert callable(view_account), (
        "IT-65R3S2 requires view_customer_account(human_user_id=..., "
        "customer_account_id=..., account_repository=...) returning account "
        "details, the viewing membership, and selected_customer_account_id."
    )
    repository_url = request.getfixturevalue("customer_test_repository_url")
    graph_iri = "urn:uad:test:it65:r3:s2:customer"
    owner = SimpleNamespace(
        human_user_id="urn:uad:test:user:it65-r3-s2",
        workos_user_id="user_it65_r3_s2_owner",
        internal_phone_number="19999999999", phone_number_verified=True,
        eligible_to_create_customer_account=True,
    )
    repository = rdf_adapter.GraphDBCustomerAccountRepository(
        repository_url=repository_url, graph_iri=graph_iri,
    )
    first_information = {
        "display_name": "First solo account", "primary_contact_name": "Solo Contact",
        "primary_contact_email": "solo@example.test",
    }
    selected_information = {
        "company_name": "Selected Appraisal Company",
        "display_name": "Selected company account",
        "primary_contact_name": "Company Contact",
        "primary_contact_email": "company@example.test",
        "contact_telephone": "19999999977",
        "postal_address": "456 Selected Street, Denver, CO 80202",
        "company_website": "https://selected.example.test",
    }
    created = []
    for account_type, information in (("solo", first_information), ("company", selected_information)):
        created.append(accounts.create_customer_account(
            person=owner, id_generator=accounts.UniqueCustomerAccountIdGenerator(),
            account_repository=repository, audit_history=AuditHistory(),
            account_type=account_type, account_information=information,
        ))
    first_id, selected_id = (account.customer_account_id for account in created)
    del repository
    data_before = _read_graph(repository_url, graph_iri)
    attribution_before = _read_graph(repository_url, PROVENANCE_GRAPH)
    fresh = rdf_adapter.GraphDBCustomerAccountRepository(
        repository_url=repository_url, graph_iri=graph_iri,
    )
    selected = view_account(
        human_user_id=owner.human_user_id, customer_account_id=selected_id,
        account_repository=fresh,
    )
    assert selected.selected_customer_account_id == selected_id
    assert selected.account.customer_account_id == selected_id
    assert selected.account.account_type == "company"
    assert selected.account.status == "active"
    assert selected.account == fresh.get(selected_id), "Display details must come from the persisted account."
    for field_name, expected in selected_information.items():
        assert getattr(selected.account, field_name) == expected
    assert selected.membership.human_user_id == owner.human_user_id
    assert selected.membership.customer_account_id == selected_id
    assert selected.membership.active is True
    assert selected.membership.role == accounts.CustomerAccountRole.OWNER

    # Selection is explicit per request. Viewing another authorized account must
    # not mutate the context already handed to account-specific work.
    other = view_account(
        human_user_id=owner.human_user_id, customer_account_id=first_id,
        account_repository=fresh,
    )
    assert other.selected_customer_account_id == first_id
    assert other.account.customer_account_id == first_id
    assert other.membership.customer_account_id == first_id
    assert other.account.account_type == "solo"
    for field_name, expected in first_information.items():
        assert getattr(other.account, field_name) == expected
    assert selected.selected_customer_account_id == selected_id
    assert selected.account.customer_account_id == selected_id
    assert selected.account.display_name == selected_information["display_name"]
    assert isomorphic(_normalized_strings(data_before), _normalized_strings(_read_graph(repository_url, graph_iri)))
    assert isomorphic(
        _normalized_strings(attribution_before),
        _normalized_strings(_read_graph(repository_url, PROVENANCE_GRAPH)),
    ), "Viewing an account must not alter customer data or create change records."
