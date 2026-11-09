"""IT-64R2S3: report an actionable SHACL validation failure."""

import os
from urllib.parse import urlsplit
from pathlib import Path
from uuid import uuid4

import pytest

from owb_graphdb.client import GraphDBClient
from owb_graphdb.configuration import RepositoryConfiguration
from owb_graphdb.setup import setup_repository

from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.compare import isomorphic
from rdflib.namespace import RDF, XSD

from app.adapters.customer_rdf_store import CustomerRdfStore




PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEST_SHAPES = """
@prefix customer: <urn:uad:customer:> .
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix test: <urn:uad:test:it64:shapes:> .

test:Account a sh:NodeShape ;
    sh:targetClass customer:CustomerAccount ;
    sh:property [ sh:path customer:name ; sh:minCount 1 ;
                  sh:maxCount 1 ; sh:datatype xsd:string ] ;
    sh:property [ sh:path customer:createdAt ; sh:minCount 1 ;
                  sh:maxCount 1 ; sh:datatype xsd:dateTime ] .

test:Membership a sh:NodeShape ;
    sh:targetClass customer:Membership ;
    sh:property [ sh:path customer:account ; sh:minCount 1 ;
                  sh:maxCount 1 ; sh:nodeKind sh:IRI ] ;
    sh:property [ sh:path customer:user ; sh:minCount 1 ;
                  sh:maxCount 1 ; sh:nodeKind sh:IRI ] ;
    sh:property [ sh:path customer:role ; sh:minCount 1 ;
                  sh:maxCount 1 ; sh:nodeKind sh:IRI ] .
"""


@pytest.fixture
def customer_test_repository_url(tmp_path):
    """Own the default repository lifecycle; never delete an explicit override."""
    configured = os.environ.get("UAD_CUSTOMER_RDF_TEST_REPOSITORY_URL", "").strip()
    if configured:
        # Existing opt-in behavior: the operator supplies a dedicated test
        # repository already provisioned with the intended customer shapes.
        yield configured
        return

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
            shapes_version="it64-r2-s3-test-v1",
            data_graph_iris=("urn:uad:test:it64:r2:s3:customer",),
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

def test_it_64_r2_s3_report_actionable_shacl_validation_failure(
    customer_test_repository_url,
):
    repository_url = customer_test_repository_url
    graph_iri = "urn:uad:test:it64:r2:s3:customer"
    customer = Namespace("urn:uad:customer:")
    sh = Namespace("http://www.w3.org/ns/shacl#")
    account_id = URIRef("urn:uad:test:account:it64-r2-s3")
    user_id = URIRef("urn:uad:test:user:it64-r2-s3")
    membership = BNode()
    initial = Graph()
    initial.add((account_id, RDF.type, customer.CustomerAccount))
    initial.add((account_id, customer.name, Literal("Original name", datatype=XSD.string)))
    initial.add((account_id, customer.createdAt, Literal(
        "2026-11-05T12:00:00Z", datatype=XSD.dateTime,
    )))
    initial.add((user_id, RDF.type, customer.User))
    initial.add((membership, RDF.type, customer.Membership))
    initial.add((membership, customer.account, account_id))
    initial.add((membership, customer.user, user_id))
    initial.add((membership, customer.role, customer.Owner))

    writer = CustomerRdfStore(repository_url, graph_iri)
    writer.commit(initial, actor_id="urn:uad:test:system:it64-r2-s3")
    stored = CustomerRdfStore(repository_url, graph_iri).retrieve()
    assert isomorphic(_normalized_strings(initial), _normalized_strings(stored)), (
        "Prerequisite failed: initial conforming customer data was not persisted."
    )
    proposed = Graph()
    for triple in stored:
        proposed.add(triple)
    proposed.remove((account_id, customer.name, None))

    # Capture the real transaction identifier without replacing transport or
    # manufacturing a rejection. All requests still reach GraphDB unchanged.
    class ObservedStore(CustomerRdfStore):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.attempted_transaction_url = None

        def _request(self, method, url, **kwargs):
            if method == "PUT" and "/transactions/" in urlsplit(url).path:
                self.attempted_transaction_url = url.split("?", 1)[0]
            return super()._request(method, url, **kwargs)

    changing_store = ObservedStore(repository_url, graph_iri)
    failure = None
    try:
        changing_store.commit(proposed, actor_id="urn:uad:test:system:it64-r2-s3")
    except Exception as error:
        failure = error

    try:
        assert failure is not None, (
            "IT-64R2S3 must report the nonconforming change as failed, not successful."
        )
        # Proposed application contract: callers receive parsed RDF diagnostics
        # and the attempted transaction identity on the raised exception.
        report = getattr(failure, "validation_report", None)
        assert isinstance(report, Graph), (
            "IT-64R2S3 requires the raised validation failure to expose "
            "validation_report as an rdflib.Graph; a raw HTTP error is not "
            "an application-readable SHACL report. "
            f"Received {type(failure).__name__}."
        )
        reports = list(report.subjects(RDF.type, sh.ValidationReport))
        assert reports, "The failure must contain a SHACL ValidationReport."
        matching_results = [
            result
            for report_node in reports
            if (report_node, sh.conforms, Literal(False)) in report
            for result in report.objects(report_node, sh.result)
            if (result, sh.focusNode, account_id) in report
            and (result, sh.resultPath, customer.name) in report
            and (result, sh.sourceConstraintComponent, sh.MinCountConstraintComponent) in report
        ]
        assert matching_results, (
            "The report must identify the attempted account, customer:name path, "
            "and violated MinCountConstraintComponent in the same validation result."
        )
        assert changing_store.attempted_transaction_url is not None
        assert getattr(failure, "transaction_url", None) == changing_store.attempted_transaction_url, (
            "The validation failure must identify the actual attempted GraphDB "
            "transaction through transaction_url."
        )
        actual = CustomerRdfStore(repository_url, graph_iri).retrieve()
        assert isomorphic(_normalized_strings(stored), _normalized_strings(actual)), (
            "The rejected customer change must leave committed RDF unchanged."
        )
    finally:
        # Release the response if the current implementation exposes HTTPError.
        close = getattr(failure, "close", None)
        if callable(close):
            close()
