"""IT-65R4S4: reject an update based on an obsolete account snapshot."""

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
            shapes_version="it65-r4-s4-test-v1",
            data_graph_iris=("urn:uad:test:it65:r4:s4:customer",),
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


def test_it_65_r4_s4_detect_conflicting_updates(request):
    update = getattr(accounts, "update_customer_account_information", None)
    assert callable(update), "IT-65R4S4 requires an account-information update service."
    assert "account_information" in signature(update).parameters
    repository_url = request.getfixturevalue("customer_test_repository_url")
    graph_iri = "urn:uad:test:it65:r4:s4:customer"
    first_actor = "urn:uad:test:user:it65-r4-s4-first"
    second_actor = "urn:uad:test:user:it65-r4-s4-second"
    first = rdf_adapter.GraphDBCustomerAccountRepository(
        repository_url=repository_url, graph_iri=graph_iri,
    )
    second = rdf_adapter.GraphDBCustomerAccountRepository(
        repository_url=repository_url, graph_iri=graph_iri,
    )
    created = accounts.create_customer_account(
        person=SimpleNamespace(
            human_user_id=first_actor, workos_user_id="user_it65_r4_s4_first",
            internal_phone_number="19999999999", phone_number_verified=True,
            eligible_to_create_customer_account=True,
        ),
        id_generator=accounts.UniqueCustomerAccountIdGenerator(),
        account_repository=first, audit_history=AuditHistory(),
        account_type="solo",
        account_information={
            "display_name": "Original account",
            "primary_contact_name": "Original Contact",
            "primary_contact_email": "original@example.test",
            "postal_address": "100 Original Street",
        },
    )
    account_id = created.customer_account_id
    customer = Namespace("urn:uad:customer:")
    membership = URIRef("urn:uad:test:membership:it65-r4-s4-second")
    additions = Graph()
    additions.add((URIRef(second_actor), RDF.type, customer.User))
    additions.add((membership, RDF.type, customer.Membership))
    additions.add((membership, customer.account, URIRef(account_id)))
    additions.add((membership, customer.user, URIRef(second_actor)))
    additions.add((membership, customer.humanUserId, Literal(second_actor, datatype=XSD.string)))
    additions.add((membership, customer.role, customer.Owner))
    additions.add((membership, customer.active, Literal(True)))
    rdf_adapter.CustomerRdfStore(
        repository_url=repository_url, graph_iri=graph_iri,
    ).apply_change(additions=additions, removals=Graph(), actor_id=first_actor)

    # Distinct application sessions read the same committed account before
    # either administrator submits a change.
    first_snapshot = first.get(account_id)
    second_snapshot = second.get(account_id)
    assert first_snapshot == second_snapshot
    for actor in (first_actor, second_actor):
        assert any(
            member.human_user_id == actor
            and member.active
            and member.role == accounts.CustomerAccountRole.OWNER
            and member.customer_account_id == account_id
            for member in first_snapshot.memberships
        ), "Both administrators must be authorized; this is not an access-denial test."

    update(
        customer_account=first_snapshot,
        account_information={
            "display_name": "First administrator saved this",
            "primary_contact_email": "first@example.test",
        },
        actor_id=first_actor, account_repository=first, audit_history=AuditHistory(),
    )
    observer = rdf_adapter.GraphDBCustomerAccountRepository(
        repository_url=repository_url, graph_iri=graph_iri,
    )
    committed = observer.get(account_id)
    assert committed.display_name == "First administrator saved this"
    assert committed.primary_contact_email == "first@example.test"
    assert committed != second_snapshot
    data_after_first = _read_graph(repository_url, graph_iri)
    attribution_after_first = _read_graph(repository_url, PROVENANCE_GRAPH)

    # These values are valid individually. The request is invalid because it
    # is based on the earlier snapshot, not because of its information or role.
    history = AuditHistory()
    failure = None
    try:
        update(
            customer_account=second_snapshot,
            account_information={
                "display_name": "Stale second administrator rename",
                "postal_address": "200 Must Not Be Saved Street",
            },
            actor_id=second_actor, account_repository=second, audit_history=history,
        )
    except Exception as error:
        failure = error

    try:
        assert failure is not None, (
            "IT-65R4S4 requires a conflict when an administrator submits an "
            "update based on the earlier account state; the stale update was accepted."
        )
        # Reuse the existing IT-64 stale-resource conflict contract.
        assert getattr(failure, "code", None) == "stale_resource_version", (
            "IT-65R4S4 requires an identifiable stale_resource_version conflict; "
            f"received {type(failure).__name__}."
        )
        assert getattr(failure, "resource_iri", None) == account_id
        assert getattr(failure, "refresh_required", None) is True
        assert str(failure).strip(), "The conflict must explain that the account changed."

        fresh = rdf_adapter.GraphDBCustomerAccountRepository(
            repository_url=repository_url, graph_iri=graph_iri,
        )
        assert fresh.get(account_id) == committed, (
            "The first administrator's committed account must remain unchanged."
        )
        assert isomorphic(
            _normalized_strings(data_after_first),
            _normalized_strings(_read_graph(repository_url, graph_iri)),
        ), "No part of the stale update may be persisted."
        assert isomorphic(
            _normalized_strings(attribution_after_first),
            _normalized_strings(_read_graph(repository_url, PROVENANCE_GRAPH)),
        ), "The rejected update must not create committed-change attribution."
        assert not any(
            event.get("event_type") == "customer_account_information_updated"
            for event in history.events
        ), "A conflict must not be reported as a successful update."
    finally:
        close = getattr(failure, "close", None)
        if callable(close):
            close()
