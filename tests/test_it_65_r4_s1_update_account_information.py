"""IT-65R4S1: durably update account information while preserving ownership."""

import os
from datetime import datetime, timezone
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
            shapes_version="it65-r4-s1-test-v1",
            data_graph_iris=("urn:uad:test:it65:r4:s1:customer",),
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
def test_it_65_r4_s1_update_account_information(request, account_type):
    update = getattr(accounts, "update_customer_account_information", None)
    assert callable(update), "IT-65R4S1 requires an account-information update service."
    assert "account_information" in signature(update).parameters, (
        "IT-65R4S1 requires update_customer_account_information to accept "
        "account_information containing valid changes to editable account fields."
    )

    repository_url = request.getfixturevalue("customer_test_repository_url")
    graph_iri = "urn:uad:test:it65:r4:s1:customer"
    actor_id = "urn:uad:test:user:it65-r4-s1-owner"
    owner = SimpleNamespace(
        human_user_id=actor_id, workos_user_id="user_it65_r4_s1",
        internal_phone_number="19999999999", phone_number_verified=True,
        eligible_to_create_customer_account=True,
    )
    repository = rdf_adapter.GraphDBCustomerAccountRepository(
        repository_url=repository_url, graph_iri=graph_iri,
    )
    original = {
        "display_name": "Original account",
        "primary_contact_name": "Original Contact",
        "primary_contact_email": "original@example.test",
        "contact_telephone": "19999999988",
        "postal_address": "100 Original Street",
    }
    changed = {
        "display_name": "Updated account",
        "primary_contact_name": "Updated Contact",
        "primary_contact_email": "updated@example.test",
        "contact_telephone": "19999999977",
        "postal_address": "200 Updated Street",
    }
    if account_type == "company":
        original.update(company_name="Original Company", company_website="https://original.example.test")
        changed.update(company_name="Updated Company", company_website="https://updated.example.test")
    created = accounts.create_customer_account(
        person=owner, id_generator=accounts.UniqueCustomerAccountIdGenerator(),
        account_repository=repository, audit_history=AuditHistory(),
        account_type=account_type, account_information=original,
    )
    account_id = created.customer_account_id
    account_iri = URIRef(account_id)

    # Test-owned persisted resources exercise preservation of incoming account
    # links and resource contents. This does not exercise credit issuance rules.
    customer = Namespace("urn:uad:customer:")
    fixture = Namespace("urn:uad:test:it65:r4:s1:owned:")
    owned = Graph()
    for name, resource_type in (
        ("credits", fixture.CreditLot),
        ("report", fixture.ValidationReport),
        ("cycle", fixture.ValidationCycle),
    ):
        resource = fixture[name]
        owned.add((resource, RDF.type, resource_type))
        owned.add((resource, customer.account, account_iri))
        owned.add((resource, fixture.marker, Literal("preserve-" + name)))
    owned.add((fixture.credits, fixture.remainingQuantity, Literal(17, datatype=XSD.integer)))
    store = CustomerRdfStore(repository_url=repository_url, graph_iri=graph_iri)
    store.apply_change(additions=owned, removals=Graph(), actor_id=actor_id)

    before = _read_graph(repository_url, graph_iri)
    records_before = _read_graph(repository_url, PROVENANCE_GRAPH)
    previous_activities = set(records_before.subjects(RDF.type, PROV.Activity))
    # Use the trusted persisted aggregate, not user-supplied membership claims.
    persisted = repository.get(account_id)
    assert persisted.status == "active"
    started = datetime.now(timezone.utc)
    update(
        customer_account=persisted, account_information=changed,
        actor_id=actor_id, account_repository=repository,
        audit_history=AuditHistory(),
    )
    finished = datetime.now(timezone.utc)

    fresh = rdf_adapter.GraphDBCustomerAccountRepository(
        repository_url=repository_url, graph_iri=graph_iri,
    )
    retrieved = fresh.get(account_id)
    assert retrieved.customer_account_id == account_id
    for field_name, expected in changed.items():
        assert getattr(retrieved, field_name) == expected, field_name
    assert retrieved.memberships == persisted.memberships
    assert retrieved.created_at == persisted.created_at
    assert retrieved.account_type == persisted.account_type
    assert retrieved.status == persisted.status
    assert retrieved.is_ownership_boundary == persisted.is_ownership_boundary
    assert retrieved.is_billing_boundary == persisted.is_billing_boundary

    after = _read_graph(repository_url, graph_iri)
    # All RDF except the edited account-field triples must remain equivalent.
    editable_predicates = {
        customer.name, customer.primaryContactName, customer.primaryContactEmail,
        customer.contactTelephone, customer.postalAddress,
    }
    if account_type == "company":
        editable_predicates.update({customer.companyName, customer.companyWebsite})

    def preserved(graph):
        result = Graph()
        for triple in graph:
            if triple[0] != account_iri or triple[1] not in editable_predicates:
                result.add(triple)
        return _normalized_strings(result)

    assert isomorphic(preserved(before), preserved(after)), (
        "Updating account information must preserve memberships, owned credits, "
        "validation work, and every unrelated stored triple."
    )

    # Require new durable attribution; the in-memory audit spy cannot satisfy it.
    records_after = _read_graph(repository_url, PROVENANCE_GRAPH)
    activities = set(records_after.subjects(RDF.type, PROV.Activity)) - previous_activities
    matching = [
        activity for activity in activities
        if (activity, CHANGE.affectedResource, account_iri) in records_after
        and (activity, PROV.wasAssociatedWith, URIRef(actor_id)) in records_after
    ]
    assert matching, "The persisted update must identify the account and acting UAD user."
    for activity in matching:
        timestamps = list(records_after.objects(activity, PROV.startedAtTime))
        assert len(timestamps) == 1
        timestamp = timestamps[0]
        assert isinstance(timestamp, Literal) and timestamp.datatype == XSD.dateTime
        recorded = timestamp.toPython()
        assert isinstance(recorded, datetime) and recorded.tzinfo is not None
        assert started <= recorded <= finished, "Attribution must record this update's time."
