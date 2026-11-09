"""IT-64R2S4: reject deletion that invalidates customer relationships."""

import os
from pathlib import Path
from uuid import uuid4

import pytest

from owb_graphdb.client import GraphDBClient
from owb_graphdb.configuration import RepositoryConfiguration
from owb_graphdb.setup import setup_repository

from rdflib import Graph, Literal, Namespace, URIRef
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
            shapes_version="it64-r2-s4-test-v1",
            data_graph_iris=("urn:uad:test:it64:r2:s4:customer",),
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

def test_it_64_r2_s4_reject_deletion_invalidating_customer_relationships(
    customer_test_repository_url,
):
    repository_url = customer_test_repository_url
    graph_iri = "urn:uad:test:it64:r2:s4:customer"
    customer = Namespace("urn:uad:customer:")
    sh = Namespace("http://www.w3.org/ns/shacl#")
    account_id = URIRef("urn:uad:test:account:it64-r2-s4")
    user_id = URIRef("urn:uad:test:user:it64-r2-s4")
    membership = URIRef("urn:uad:test:membership:it64-r2-s4")
    initial = Graph()
    initial.add((account_id, RDF.type, customer.CustomerAccount))
    initial.add((account_id, customer.name, Literal("Account to retain", datatype=XSD.string)))
    initial.add((account_id, customer.createdAt, Literal(
        "2026-11-05T12:00:00Z", datatype=XSD.dateTime,
    )))
    initial.add((user_id, RDF.type, customer.User))
    initial.add((membership, RDF.type, customer.Membership))
    initial.add((membership, customer.account, account_id))
    initial.add((membership, customer.user, user_id))
    initial.add((membership, customer.role, customer.Owner))

    writer = CustomerRdfStore(repository_url, graph_iri)
    writer.commit(initial, actor_id="urn:uad:test:system:it64-r2-s4")
    stored = CustomerRdfStore(repository_url, graph_iri).retrieve()
    assert isomorphic(_normalized_strings(initial), _normalized_strings(stored)), (
        "Prerequisite failed: the conforming account and membership were not persisted."
    )

    # Express deletion through the existing whole-graph commit API. The
    # membership and its account relationship remain; the target loses its data.
    proposed = Graph()
    for triple in stored:
        proposed.add(triple)
    proposed.remove((account_id, None, None))
    assert (membership, customer.account, account_id) in proposed
    assert not list(proposed.triples((account_id, None, None)))

    failure = None
    try:
        writer.commit(proposed, actor_id="urn:uad:test:system:it64-r2-s4")
    except Exception as error:
        failure = error

    try:
        # Read before teardown so cleanup cannot conceal an accepted deletion.
        actual = CustomerRdfStore(repository_url, graph_iri).retrieve()
        assert failure is not None, (
            "IT-64R2S4 requires rejection when deleting account data leaves "
            "a membership pointing to a target that fails its active shape."
        )
        report = getattr(failure, "validation_report", None)
        assert isinstance(report, Graph), (
            "Deletion must be rejected by SHACL with a validation report; "
            f"an unrelated {type(failure).__name__} is not sufficient."
        )
        matching_results = [
            result
            for report_node in report.subjects(RDF.type, sh.ValidationReport)
            if (report_node, sh.conforms, Literal(False)) in report
            for result in report.objects(report_node, sh.result)
            if (result, sh.focusNode, membership) in report
            and (result, sh.resultPath, customer.account) in report
            and (result, sh.sourceConstraintComponent, sh.NodeConstraintComponent) in report
        ]
        assert matching_results, (
            "The SHACL report must identify the membership's account relationship "
            "as violating its target-node shape constraint."
        )
        assert (membership, customer.account, account_id) in actual, (
            "The rejected deletion must preserve the original relationship."
        )
        assert isomorphic(_normalized_strings(stored), _normalized_strings(actual)), (
            "IT-64R2S4 requires the relationship, its target, and all previously "
            "committed customer RDF to remain unchanged after rejection."
        )
    finally:
        close = getattr(failure, "close", None)
        if callable(close):
            close()
