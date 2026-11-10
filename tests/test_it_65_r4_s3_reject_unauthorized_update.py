"""IT-65R4S3: reject unauthorized updates and preserve persisted data."""

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
            shapes_version="it65-r4-s3-test-v1",
            data_graph_iris=("urn:uad:test:it65:r4:s3:customer",),
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


def test_it_65_r4_s3_reject_unauthorized_update(request):
    update = getattr(accounts, "update_customer_account_information", None)
    assert callable(update), "IT-65R4S3 requires an account-information update service."
    assert "account_information" in signature(update).parameters

    repository_url = request.getfixturevalue("customer_test_repository_url")
    graph_iri = "urn:uad:test:it65:r4:s3:customer"
    repository = rdf_adapter.GraphDBCustomerAccountRepository(
        repository_url=repository_url, graph_iri=graph_iri,
    )
    customer = Namespace("urn:uad:customer:")
    owner_id = "urn:uad:test:user:it65-r4-s3-owner"
    unrelated_id = "urn:uad:test:user:it65-r4-s3-other-owner"

    def create(actor_id, name):
        return accounts.create_customer_account(
            person=SimpleNamespace(
                human_user_id=actor_id, workos_user_id="workos_" + name,
                internal_phone_number="19999999999", phone_number_verified=True,
                eligible_to_create_customer_account=True,
            ),
            id_generator=accounts.UniqueCustomerAccountIdGenerator(),
            account_repository=repository, audit_history=AuditHistory(),
            account_type="solo",
            account_information={
                "display_name": name, "primary_contact_name": "Stored Contact",
                "primary_contact_email": "stored@example.test",
            },
        )

    target = create(owner_id, "Protected account")
    other = create(unrelated_id, "Other account")
    account_iri = URIRef(target.customer_account_id)
    # Owning another account must not confer authority over this account.
    assert other.customer_account_id != target.customer_account_id

    cases = [("unrelated-owner", unrelated_id)]
    additions = Graph()
    for label, role, active in (
        ("reviewer", customer.Reviewer, True),
        ("validator", customer.Validator, True),
        ("billing-administrator", customer.BillingAdministrator, True),
        ("inactive-owner", customer.Owner, False),
    ):
        actor_id = "urn:uad:test:user:it65-r4-s3-" + label
        user = URIRef(actor_id)
        membership = URIRef("urn:uad:test:membership:it65-r4-s3-" + label)
        additions.add((user, RDF.type, customer.User))
        additions.add((membership, RDF.type, customer.Membership))
        additions.add((membership, customer.account, account_iri))
        additions.add((membership, customer.user, user))
        additions.add((membership, customer.humanUserId, Literal(actor_id, datatype=XSD.string)))
        additions.add((membership, customer.role, role))
        additions.add((membership, customer.active, Literal(active)))
        cases.append((label, actor_id))
    rdf_adapter.CustomerRdfStore(
        repository_url=repository_url, graph_iri=graph_iri,
    ).apply_change(additions=additions, removals=Graph(), actor_id=owner_id)

    baseline = repository.get(target.customer_account_id)
    other_before = repository.get(other.customer_account_id)
    assert baseline.status == "active"
    data_before = _read_graph(repository_url, graph_iri)
    attribution_before = _read_graph(repository_url, PROVENANCE_GRAPH)

    for label, actor_id in cases:
        # Inputs are otherwise valid: authorization must be the reason for denial.
        history = AuditHistory()
        with pytest.raises(PermissionError):
            update(
                customer_account=repository.get(target.customer_account_id),
                account_information={
                    "display_name": "Unauthorized rename",
                    "primary_contact_name": "Unauthorized Contact",
                    "primary_contact_email": "unauthorized@example.test",
                },
                actor_id=actor_id, account_repository=repository,
                audit_history=history,
            )
        fresh = rdf_adapter.GraphDBCustomerAccountRepository(
            repository_url=repository_url, graph_iri=graph_iri,
        )
        assert fresh.get(target.customer_account_id) == baseline, label
        assert fresh.get(other.customer_account_id) == other_before, label
        assert isomorphic(
            _normalized_strings(data_before),
            _normalized_strings(_read_graph(repository_url, graph_iri)),
        ), f"{label}: denial must preserve all stored customer data."
        assert isomorphic(
            _normalized_strings(attribution_before),
            _normalized_strings(_read_graph(repository_url, PROVENANCE_GRAPH)),
        ), f"{label}: denial must not produce committed-change attribution."
        assert not any(
            event.get("event_type") == "customer_account_information_updated"
            for event in history.events
        ), f"{label}: denial must not report a successful update."
