"""IT-65R6S3: reject closure without active ownership in the target account."""

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
            shapes_version="it65-r6-s3-test-v1",
            data_graph_iris=("urn:uad:test:it65:r6:s3:customer",),
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
    """All closure prerequisites other than owner authorization are satisfied."""

    def get_account_obligations(self, customer_account_id):
        return SimpleNamespace(
            remaining_validation_credits=0,
            validation_work_in_progress=0,
            pending_purchases=0,
            unresolved_payment_obligations=0,
        )


def test_it_65_r6_s3_reject_closure_by_user_without_owner_permission(request):
    close = getattr(lifecycle, "request_customer_account_closure", None)
    assert callable(close), "IT-65R6S3 requires the account-closure request service."
    repository_url = request.getfixturevalue("customer_test_repository_url")
    graph_iri = "urn:uad:test:it65:r6:s3:customer"
    owner_id = "urn:uad:test:user:it65-r6-s3-owner"
    other_owner_id = "urn:uad:test:user:it65-r6-s3-other-owner"
    repository = rdf_adapter.GraphDBCustomerAccountRepository(
        repository_url=repository_url, graph_iri=graph_iri,
    )

    def create(user_id, name):
        return accounts.create_customer_account(
            person=SimpleNamespace(
                human_user_id=user_id, workos_user_id="workos_" + name,
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

    target = create(owner_id, "Protected company")
    other = create(other_owner_id, "Other company")
    account_id = target.customer_account_id
    customer = Namespace("urn:uad:customer:")
    cases = [
        ("owner-of-other-account", other_owner_id),
        ("unrelated-user", "urn:uad:test:user:it65-r6-s3-unrelated"),
    ]
    additions = Graph()
    for label, role, active in (
        ("billing-administrator", customer.BillingAdministrator, True),
        ("validator", customer.Validator, True),
        ("reviewer", customer.Reviewer, True),
        ("inactive-owner", customer.Owner, False),
    ):
        user_id = "urn:uad:test:user:it65-r6-s3-" + label
        node = URIRef("urn:uad:test:membership:it65-r6-s3-" + label)
        additions.add((URIRef(user_id), RDF.type, customer.User))
        additions.add((node, RDF.type, customer.Membership))
        additions.add((node, customer.account, URIRef(account_id)))
        additions.add((node, customer.user, URIRef(user_id)))
        additions.add((node, customer.humanUserId, Literal(user_id, datatype=XSD.string)))
        additions.add((node, customer.role, role))
        additions.add((node, customer.active, Literal(active)))
        cases.append((label, user_id))
    rdf_adapter.CustomerRdfStore(
        repository_url=repository_url, graph_iri=graph_iri,
    ).apply_change(additions=additions, removals=Graph(), actor_id=owner_id)

    baseline = repository.get(account_id)
    other_before = repository.get(other.customer_account_id)
    assert baseline.status == "active"
    before = _read_graph(repository_url, graph_iri)
    attribution_before = _read_graph(repository_url, PROVENANCE_GRAPH)
    for label, actor_id in cases:
        assert not any(
            member.active and member.role == accounts.CustomerAccountRole.OWNER
            and member.human_user_id == actor_id
            and member.customer_account_id == account_id
            for member in baseline.memberships
        ), label
        history = AuditHistory()
        # Confirmation and zero obligations ensure that missing owner
        # permission is the reason closure must be denied.
        with pytest.raises(PermissionError):
            close(
                actor_id=actor_id, customer_account_id=account_id, confirmed=True,
                account_repository=repository,
                obligation_repository=ClearObligations(), audit_history=history,
            )
        fresh = rdf_adapter.GraphDBCustomerAccountRepository(
            repository_url=repository_url, graph_iri=graph_iri,
        )
        assert fresh.get(account_id) == baseline, label
        assert fresh.get(account_id).status == "active", label
        assert fresh.get(other.customer_account_id) == other_before, label
        assert isomorphic(
            _normalized_strings(before),
            _normalized_strings(_read_graph(repository_url, graph_iri)),
        ), f"{label}: unauthorized closure must preserve customer RDF."
        assert isomorphic(
            _normalized_strings(attribution_before),
            _normalized_strings(_read_graph(repository_url, PROVENANCE_GRAPH)),
        ), f"{label}: unauthorized closure must not create committed-change attribution."
        assert not any(
            event.get("event_type") == "customer_account_closed"
            for event in history.events
        ), f"{label}: unauthorized closure must not report success."
