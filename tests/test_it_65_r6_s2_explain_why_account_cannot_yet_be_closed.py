"""IT-65R6S2: identify closure blockers and preserve the active account."""

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
            shapes_version="it65-r6-s2-test-v1",
            data_graph_iris=("urn:uad:test:it65:r6:s2:customer",),
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


OBLIGATION_FIELDS = (
    "remaining_validation_credits",
    "validation_work_in_progress",
    "pending_purchases",
    "unresolved_payment_obligations",
)


class OutstandingObligations:
    """Controlled obligations boundary, not production billing reconciliation."""

    def __init__(self, values):
        self.values = dict(values)
        self.requests = []

    def get_account_obligations(self, customer_account_id):
        self.requests.append(customer_account_id)
        return SimpleNamespace(**self.values)


@pytest.mark.parametrize(
    "outstanding",
    [
        {"remaining_validation_credits": 7},
        {"validation_work_in_progress": 2},
        {"pending_purchases": 1},
        {"unresolved_payment_obligations": 3},
        dict(zip(OBLIGATION_FIELDS, (7, 2, 1, 3))),
    ],
    ids=["credits", "work-in-progress", "pending-purchase", "payment-obligations", "all-blockers"],
)
def test_it_65_r6_s2_explain_why_account_cannot_yet_be_closed(request, outstanding):
    close = getattr(lifecycle, "request_customer_account_closure", None)
    assert callable(close), "IT-65R6S2 requires the account-closure request service."
    repository_url = request.getfixturevalue("customer_test_repository_url")
    graph_iri = "urn:uad:test:it65:r6:s2:customer"
    actor_id = "urn:uad:test:user:it65-r6-s2-owner"
    repository = rdf_adapter.GraphDBCustomerAccountRepository(
        repository_url=repository_url, graph_iri=graph_iri,
    )
    created = accounts.create_customer_account(
        person=SimpleNamespace(
            human_user_id=actor_id, workos_user_id="user_it65_r6_s2_owner",
            internal_phone_number="19999999999", phone_number_verified=True,
            eligible_to_create_customer_account=True,
        ),
        id_generator=accounts.UniqueCustomerAccountIdGenerator(),
        account_repository=repository, audit_history=AuditHistory(),
        account_type="company",
        account_information={
            "display_name": "Account with obligations",
            "company_name": "Existing Company",
            "primary_contact_name": "Owner Contact",
            "primary_contact_email": "owner@example.test",
        },
    )
    account_id = created.customer_account_id
    baseline = repository.get(account_id)
    assert baseline.status == "active"
    assert any(
        member.active and member.human_user_id == actor_id
        and member.role == accounts.CustomerAccountRole.OWNER
        for member in baseline.memberships
    )
    before = _read_graph(repository_url, graph_iri)
    attribution_before = _read_graph(repository_url, PROVENANCE_GRAPH)
    values = {field: 0 for field in OBLIGATION_FIELDS}
    values.update(outstanding)
    obligations = OutstandingObligations(values)
    history = AuditHistory()

    with pytest.raises(ValueError) as rejected:
        close(
            actor_id=actor_id, customer_account_id=account_id, confirmed=True,
            account_repository=repository, obligation_repository=obligations,
            audit_history=history,
        )

    assert obligations.requests and set(obligations.requests) == {account_id}
    # Existing closure diagnostics use these domain field names. Require every
    # outstanding condition, not just a generic "cannot close" explanation.
    explanation = str(rejected.value).casefold().replace("_", " ").replace("-", " ")
    for field in outstanding:
        assert field.replace("_", " ") in explanation, (
            f"IT-65R6S2 must identify the outstanding {field} condition."
        )
    for field in set(OBLIGATION_FIELDS) - set(outstanding):
        assert field.replace("_", " ") not in explanation, (
            f"Zero-valued {field} must not be reported as an outstanding condition."
        )

    fresh = rdf_adapter.GraphDBCustomerAccountRepository(
        repository_url=repository_url, graph_iri=graph_iri,
    )
    persisted = fresh.get(account_id)
    assert persisted.status == "active"
    assert persisted == baseline
    assert isomorphic(
        _normalized_strings(before),
        _normalized_strings(_read_graph(repository_url, graph_iri)),
    ), "A blocked closure must preserve all stored customer RDF."
    assert isomorphic(
        _normalized_strings(attribution_before),
        _normalized_strings(_read_graph(repository_url, PROVENANCE_GRAPH)),
    ), "A blocked closure must not create committed-change attribution."
    assert not any(
        event.get("event_type") == "customer_account_closed"
        for event in history.events
    ), "A blocked closure must not report success."
