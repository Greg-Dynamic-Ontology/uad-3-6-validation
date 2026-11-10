"""IT-65R5S3: durably deactivate a company membership without deleting identity or work."""

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
            shapes_version="it65-r5-s3-test-v1",
            data_graph_iris=("urn:uad:test:it65:r5:s3:customer",),
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


@pytest.mark.parametrize("another_active_role", [False, True], ids=["no-other-role", "retains-validator-role"])
def test_it_65_r5_s3_remove_users_company_membership(request, another_active_role):
    repository_url = request.getfixturevalue("customer_test_repository_url")
    graph_iri = "urn:uad:test:it65:r5:s3:customer"
    owner_id = "urn:uad:test:user:it65-r5-s3-owner"
    user_id = "urn:uad:test:user:it65-r5-s3-member"
    repository = rdf_adapter.GraphDBCustomerAccountRepository(
        repository_url=repository_url, graph_iri=graph_iri,
    )
    created = accounts.create_customer_account(
        person=SimpleNamespace(
            human_user_id=owner_id, workos_user_id="user_it65_r5_s3_owner",
            internal_phone_number="19999999999", phone_number_verified=True,
            eligible_to_create_customer_account=True,
        ),
        id_generator=accounts.UniqueCustomerAccountIdGenerator(),
        account_repository=repository, audit_history=AuditHistory(),
        account_type="company",
        account_information={
            "display_name": "Membership removal company",
            "company_name": "Existing Company",
            "primary_contact_name": "Owner Contact",
            "primary_contact_email": "owner@example.test",
        },
    )
    account_id = created.customer_account_id
    for role in (
        [accounts.CustomerAccountRole.REVIEWER, accounts.CustomerAccountRole.VALIDATOR]
        if another_active_role else [accounts.CustomerAccountRole.REVIEWER]
    ):
        memberships.grant_customer_account_membership(
            actor_id=owner_id, human_user_id=user_id, customer_account_id=account_id,
            role=role, account_repository=repository, audit_history=AuditHistory(),
        )

    customer = Namespace("urn:uad:customer:")
    fixture = Namespace("urn:uad:test:it65:r5:s3:owned:")
    additions = Graph()
    # Persisted ownership sentinels exercise preservation, not credit issuance.
    for name, kind in (
        ("credits", fixture.CreditLot),
        ("report", fixture.ValidationReport),
        ("cycle", fixture.ValidationCycle),
    ):
        additions.add((fixture[name], RDF.type, kind))
        additions.add((fixture[name], customer.account, URIRef(account_id)))
        additions.add((fixture[name], fixture.marker, Literal("preserve-" + name)))
    additions.add((fixture.credits, fixture.remainingQuantity, Literal(17, datatype=XSD.integer)))
    additions.add((URIRef(user_id), URIRef("https://schema.org/email"), Literal("member@example.test")))
    rdf_adapter.CustomerRdfStore(
        repository_url=repository_url, graph_iri=graph_iri,
    ).apply_change(additions=additions, removals=Graph(), actor_id=owner_id)

    before = _read_graph(repository_url, graph_iri)
    stored = repository.get(account_id)
    owner = next(m for m in stored.memberships if m.human_user_id == owner_id and m.active)
    target = next(
        m for m in stored.memberships
        if m.human_user_id == user_id and m.role == accounts.CustomerAccountRole.REVIEWER
    )
    assert owner.role == accounts.CustomerAccountRole.OWNER
    assert target.active
    assert accounts.view_customer_account(
        human_user_id=user_id, customer_account_id=account_id, account_repository=repository,
    ).account.customer_account_id == account_id
    nodes = [
        node for node in before.subjects(customer.account, URIRef(account_id))
        if (node, RDF.type, customer.Membership) in before
        and (node, customer.user, URIRef(user_id)) in before
        and (node, customer.role, customer.Reviewer) in before
    ]
    assert len(nodes) == 1
    target_node = nodes[0]

    # Use the existing public removal service with real GraphDB persistence.
    memberships.remove_customer_account_membership(
        owner_membership=owner, membership=target,
        membership_repository=repository, audit_history=AuditHistory(),
    )

    fresh = rdf_adapter.GraphDBCustomerAccountRepository(
        repository_url=repository_url, graph_iri=graph_iri,
    )
    persisted = fresh.get(account_id)
    removed = [
        m for m in persisted.memberships
        if m.human_user_id == user_id and m.role == accounts.CustomerAccountRole.REVIEWER
    ]
    assert len(removed) == 1 and removed[0].active is False, (
        "Removal must durably deactivate the existing membership."
    )
    assert owner in persisted.memberships, "An active owner must remain."
    after = _read_graph(repository_url, graph_iri)
    expected = Graph()
    for triple in before:
        if triple[:2] != (target_node, customer.active):
            expected.add(triple)
    expected.add((target_node, customer.active, Literal(False)))
    assert isomorphic(_normalized_strings(expected), _normalized_strings(after)), (
        "Only the target membership's active flag may change: identity, other "
        "memberships, account credits, and validation work must be preserved."
    )

    if another_active_role:
        selected = accounts.view_customer_account(
            human_user_id=user_id, customer_account_id=account_id, account_repository=fresh,
        )
        assert selected.membership.role == accounts.CustomerAccountRole.VALIDATOR
        assert selected.membership.active
        decision = authorize_customer_activity(
            selected.membership, account_id,
            CustomerAccountActivity.SUBMIT_REPORTS_AND_MANAGE_VALIDATION_CYCLES,
        )
        assert decision.result == AuthorizationResult.ALLOWED
    else:
        with pytest.raises(PermissionError):
            accounts.view_customer_account(
                human_user_id=user_id, customer_account_id=account_id, account_repository=fresh,
            )
        assert accounts.list_customer_accounts(
            human_user_id=user_id, account_repository=fresh,
        ) == ()
    assert authorize_customer_activity(
        removed[0], account_id,
        CustomerAccountActivity.VIEW_REPORTS_FINDINGS_AND_CYCLE_HISTORIES,
    ).result == AuthorizationResult.DENIED
