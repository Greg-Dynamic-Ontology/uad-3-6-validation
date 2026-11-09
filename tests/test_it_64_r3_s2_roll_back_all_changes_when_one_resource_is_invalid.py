"""IT-64R3S2: roll back all changes when one related resource is invalid."""

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
            shapes_version="it64-r3-s2-test-v1",
            data_graph_iris=("urn:uad:test:it64:r3:s2:customer",),
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

def test_it_64_r3_s2_roll_back_all_changes_when_one_resource_is_invalid(
    customer_test_repository_url,
):
    repository_url = customer_test_repository_url
    graph_iri = "urn:uad:test:it64:r3:s2:customer"
    customer = Namespace("urn:uad:customer:")
    sh = Namespace("http://www.w3.org/ns/shacl#")
    account_id = URIRef("urn:uad:test:account:it64-r3-s2")
    user_id = URIRef("urn:uad:test:user:it64-r3-s2")
    membership = URIRef("urn:uad:test:membership:it64-r3-s2")
    old_name = Literal("Original account", datatype=XSD.string)
    new_name = Literal("Proposed account", datatype=XSD.string)
    initial = Graph()
    initial.add((account_id, RDF.type, customer.CustomerAccount))
    initial.add((account_id, customer.name, old_name))
    initial.add((account_id, customer.createdAt, Literal(
        "2026-11-05T12:00:00Z", datatype=XSD.dateTime,
    )))
    initial.add((user_id, RDF.type, customer.User))
    initial.add((membership, RDF.type, customer.Membership))
    initial.add((membership, customer.account, account_id))
    initial.add((membership, customer.user, user_id))
    initial.add((membership, customer.role, customer.Owner))

    writer = CustomerRdfStore(repository_url, graph_iri)
    writer.commit(initial, actor_id="urn:uad:test:system:it64-r3-s2")
    stored = CustomerRdfStore(repository_url, graph_iri).retrieve()
    assert isomorphic(_normalized_strings(initial), _normalized_strings(stored)), (
        "Prerequisite failed: the original conforming customer graph was not persisted."
    )

    proposed = Graph()
    for triple in stored:
        proposed.add(triple)
    # Valid change to the account, combined with an invalid membership change:
    # the active membership shape requires exactly one role IRI.
    proposed.set((account_id, customer.name, new_name))
    proposed.remove((membership, customer.role, None))

    failure = None
    try:
        writer.commit(proposed, actor_id="urn:uad:test:system:it64-r3-s2")
    except Exception as error:
        failure = error

    try:
        # Observe the persisted state before fixture teardown can remove it.
        actual = CustomerRdfStore(repository_url, graph_iri).retrieve()
        assert failure is not None, (
            "IT-64R3S2 requires rejection of the entire transaction when the "
            "proposed membership lacks its required role."
        )
        report = getattr(failure, "validation_report", None)
        assert isinstance(report, Graph), (
            "Expected a SHACL rejection report, not an unrelated "
            f"{type(failure).__name__}."
        )
        matching_results = [
            result
            for node in report.subjects(RDF.type, sh.ValidationReport)
            if (node, sh.conforms, Literal(False)) in report
            for result in report.objects(node, sh.result)
            if (result, sh.focusNode, membership) in report
            and (result, sh.resultPath, customer.role) in report
            and (result, sh.sourceConstraintComponent, sh.MinCountConstraintComponent) in report
        ]
        assert matching_results, (
            "The rejection must identify the membership's missing required role."
        )
        comparable = _normalized_strings(actual)
        assert (account_id, customer.name, old_name) in comparable, (
            "The valid account change must also be rolled back."
        )
        assert (account_id, customer.name, new_name) not in comparable, (
            "No part of the proposed account change may be committed."
        )
        assert (membership, customer.role, customer.Owner) in actual, (
            "The membership must retain its previously committed owner role."
        )
        assert isomorphic(_normalized_strings(stored), comparable), (
            "IT-64R3S2 requires every affected resource and the entire customer "
            "graph to retain their previously committed state."
        )
    finally:
        close = getattr(failure, "close", None)
        if callable(close):
            close()
