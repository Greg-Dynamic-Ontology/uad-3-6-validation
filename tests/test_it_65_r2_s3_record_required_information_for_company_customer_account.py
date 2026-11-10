"""IT-65R2S3: persist required and optional company account information."""

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
            shapes_version="it65-r2-s3-test-v1",
            data_graph_iris=("urn:uad:test:it65:r2:s3:customer",),
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


@pytest.mark.parametrize("include_optional", [False, True], ids=["optional-omitted", "optional-supplied"])
def test_it_65_r2_s3_record_required_information_for_company_customer_account(
    customer_test_repository_url, include_optional,
):
    repository_url = customer_test_repository_url
    graph_iri = "urn:uad:test:it65:r2:s3:customer"
    owner = SimpleNamespace(
        human_user_id="urn:uad:test:user:it65-r2-s3",
        workos_user_id="user_it65_r2_s3_owner",
        internal_phone_number="19999999999",
        phone_number_verified=True,
        eligible_to_create_customer_account=True,
    )
    required = {
        "company_name": "Example Appraisal Company",
        "display_name": "Company Appraisal Account",
        "primary_contact_name": "Alex Appraiser",
        "primary_contact_email": "alex@example.test",
    }
    optional = {
        "contact_telephone": "19999999999",
        "postal_address": "123 Test Street, Denver, CO 80202",
        "company_website": "https://appraisal.example.test",
    }
    submitted = dict(required)
    if include_optional:
        submitted.update(optional)
    original_submission = dict(submitted)
    repository = rdf_adapter.GraphDBCustomerAccountRepository(
        repository_url=repository_url, graph_iri=graph_iri,
    )
    created = accounts.create_customer_account(
        person=owner,
        id_generator=accounts.UniqueCustomerAccountIdGenerator(),
        account_repository=repository,
        audit_history=AuditHistory(),
        account_type="company",
        account_information=submitted,
    )
    assert submitted == original_submission, "Creation must not mutate the supplied information."
    later = rdf_adapter.GraphDBCustomerAccountRepository(
        repository_url=repository_url, graph_iri=graph_iri,
    ).get(created.customer_account_id)
    for account in (created, later):
        assert account.account_type == "company"
        assert account.status == "active"
        assert account.customer_account_id == created.customer_account_id
        for field_name, expected in required.items():
            assert getattr(account, field_name, None) == expected, (
                f"IT-65R2S3 requires the company account's {field_name} to be recorded."
            )
        for field_name, expected in optional.items():
            actual = getattr(account, field_name, None)
            if include_optional:
                assert actual == expected, f"Supplied optional {field_name} must be retained."
            else:
                assert actual in (None, ""), f"Omitted optional {field_name} must not be invented."

    # Check explicit persisted values independently of repository reconstruction.
    customer = Namespace("urn:uad:customer:")
    predicates = {
        "company_name": customer.companyName,
        "display_name": customer.name,
        "primary_contact_name": customer.primaryContactName,
        "primary_contact_email": customer.primaryContactEmail,
        "contact_telephone": customer.contactTelephone,
        "postal_address": customer.postalAddress,
        "company_website": customer.companyWebsite,
    }
    graph = _read_graph(repository_url, graph_iri)
    subject = URIRef(created.customer_account_id)
    assert set(graph.subjects(RDF.type, customer.CustomerAccount)) == {subject}
    for field_name, expected in submitted.items():
        values = list(graph.objects(subject, predicates[field_name]))
        assert len(values) == 1 and isinstance(values[0], Literal) and str(values[0]) == expected, (
            f"GraphDB must contain exactly one supplied value for {field_name}."
        )
    if not include_optional:
        for field_name in optional:
            assert all(str(value) == "" for value in graph.objects(subject, predicates[field_name]))

