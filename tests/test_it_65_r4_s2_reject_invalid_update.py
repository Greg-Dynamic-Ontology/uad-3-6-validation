"""IT-65R4S2: reject invalid updates without changing persisted account data."""

import os
from copy import deepcopy
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
            shapes_version="it65-r4-s2-test-v1",
            data_graph_iris=("urn:uad:test:it65:r4:s2:customer",),
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
def test_it_65_r4_s2_reject_invalid_update(request, account_type):
    update = getattr(accounts, "update_customer_account_information", None)
    assert callable(update), "IT-65R4S2 requires an account-information update service."
    assert "account_information" in signature(update).parameters, (
        "IT-65R4S2 requires account_information submissions."
    )
    repository_url = request.getfixturevalue("customer_test_repository_url")
    graph_iri = "urn:uad:test:it65:r4:s2:customer"
    actor_id = "urn:uad:test:user:it65-r4-s2-owner"
    owner = SimpleNamespace(
        human_user_id=actor_id, workos_user_id="user_it65_r4_s2",
        internal_phone_number="19999999999", phone_number_verified=True,
        eligible_to_create_customer_account=True,
    )
    repository = rdf_adapter.GraphDBCustomerAccountRepository(
        repository_url=repository_url, graph_iri=graph_iri,
    )
    information = {
        "display_name": "Stored account",
        "primary_contact_name": "Stored Contact",
        "primary_contact_email": "stored@example.test",
        "contact_telephone": "19999999988",
        "postal_address": "100 Stored Street",
    }
    if account_type == "company":
        information.update(
            company_name="Stored Company",
            company_website="https://stored.example.test",
        )
    created = accounts.create_customer_account(
        person=owner, id_generator=accounts.UniqueCustomerAccountIdGenerator(),
        account_repository=repository, audit_history=AuditHistory(),
        account_type=account_type, account_information=information,
    )
    account_id = created.customer_account_id
    baseline = repository.get(account_id)
    assert baseline.status == "active"
    data_before = _read_graph(repository_url, graph_iri)
    attribution_before = _read_graph(repository_url, PROVENANCE_GRAPH)

    cases = [
        ("blank-name", {"display_name": " 	 "}, {"display_name"}),
        ("blank-contact", {"primary_contact_name": ""}, {"primary_contact_name"}),
        ("invalid-email", {"primary_contact_email": "not-an-email"}, {"primary_contact_email"}),
        ("wrong-type", {"contact_telephone": 12345}, {"contact_telephone"}),
        (
            "multiple-errors",
            {
                "display_name": "",
                "primary_contact_name": " ",
                "primary_contact_email": "not-an-email",
            },
            {"display_name", "primary_contact_name", "primary_contact_email"},
        ),
    ]
    if account_type == "company":
        cases.append(("blank-company", {"company_name": " "}, {"company_name"}))

    # Reuse this test's isolated account to avoid provisioning a repository for
    # every invalid field. Each rejection is checked against the original state.
    for label, invalid_fields, expected_errors in cases:
        submission = {"postal_address": "Must not be partially saved", **invalid_fields}
        original_submission = deepcopy(submission)
        history = AuditHistory()
        try:
            update(
                customer_account=repository.get(account_id),
                account_information=submission, actor_id=actor_id,
                account_repository=repository, audit_history=history,
            )
        except Exception as error:
            assert getattr(error, "code", None) == "invalid_account_information", (
                f"{label}: expected identifiable invalid_account_information "
                f"diagnostics, received {type(error).__name__}."
            )
            diagnostics = getattr(error, "field_errors", None)
            assert isinstance(diagnostics, dict), f"{label}: missing field diagnostics."
            assert expected_errors <= set(diagnostics), (
                f"{label}: every invalid field must be identified: {expected_errors}."
            )
            for field in expected_errors:
                assert isinstance(diagnostics[field], str) and diagnostics[field].strip(), (
                    f"{label}: {field} needs a nonempty correction message."
                )
        else:
            pytest.fail(f"{label}: invalid account information was accepted.")

        assert submission == original_submission, f"{label}: submission was mutated."
        fresh = rdf_adapter.GraphDBCustomerAccountRepository(
            repository_url=repository_url, graph_iri=graph_iri,
        )
        assert fresh.get(account_id) == baseline, (
            f"{label}: a subsequent read must return the previously stored account."
        )
        assert isomorphic(
            _normalized_strings(data_before),
            _normalized_strings(_read_graph(repository_url, graph_iri)),
        ), f"{label}: rejection must preserve all stored customer RDF."
        assert isomorphic(
            _normalized_strings(attribution_before),
            _normalized_strings(_read_graph(repository_url, PROVENANCE_GRAPH)),
        ), f"{label}: rejection must not create successful-change attribution."
        assert not history.events, f"{label}: rejection must not report a successful update."
