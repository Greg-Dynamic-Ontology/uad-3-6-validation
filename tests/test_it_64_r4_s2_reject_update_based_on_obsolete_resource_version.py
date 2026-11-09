"""IT-64R4S2: reject an update based on an obsolete resource version."""

import os
from inspect import signature
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
    sh:property [ sh:path customer:label ; sh:maxCount 1 ; sh:datatype xsd:string ] ;
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
            shapes_version="it64-r4-s2-test-v1",
            data_graph_iris=("urn:uad:test:it64:r4:s2:customer",),
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

def test_it_64_r4_s2_reject_update_based_on_obsolete_resource_version(request):
    assert callable(getattr(CustomerRdfStore, "get_resource_version", None)), (
        "IT-64R4S2 requires get_resource_version(resource_iri) to return an "
        "opaque version token for persisted customer resource state."
    )
    assert "expected_versions" in signature(CustomerRdfStore.apply_change).parameters, (
        "IT-64R4S2 requires apply_change(..., expected_versions={resource_iri: version}) "
        "to reject an update based on an obsolete resource version."
    )
    repository_url = request.getfixturevalue("customer_test_repository_url")
    graph_iri = "urn:uad:test:it64:r4:s2:customer"
    customer = Namespace("urn:uad:customer:")
    account = URIRef("urn:uad:test:account:it64-r4-s2")
    membership = URIRef("urn:uad:test:membership:it64-r4-s2")
    user = URIRef("urn:uad:test:user:it64-r4-s2")
    original_name = Literal("Original account", datatype=XSD.string)
    first_name = Literal("First administrator's update", datatype=XSD.string)
    stale_label = Literal("Second administrator's stale update", datatype=XSD.string)
    initial = Graph()
    initial.add((account, RDF.type, customer.CustomerAccount))
    initial.add((account, customer.name, original_name))
    initial.add((account, customer.createdAt, Literal(
        "2026-11-05T12:00:00Z", datatype=XSD.dateTime,
    )))
    initial.add((user, RDF.type, customer.User))
    initial.add((membership, RDF.type, customer.Membership))
    initial.add((membership, customer.account, account))
    initial.add((membership, customer.user, user))
    initial.add((membership, customer.role, customer.Owner))
    CustomerRdfStore(repository_url, graph_iri).commit(
        initial, actor_id="urn:uad:test:system:it64-r4-s2",
    )

    first = CustomerRdfStore(repository_url, graph_iri)
    second = CustomerRdfStore(repository_url, graph_iri)
    for administrator in (first, second):
        assert isomorphic(_normalized_strings(initial), _normalized_strings(administrator.retrieve()))
    first_version = first.get_resource_version(str(account))
    second_version = second.get_resource_version(str(account))
    assert isinstance(first_version, str) and first_version, "Expected a nonempty opaque version token."
    assert first_version == second_version, "Both administrators must read the same initial version."

    additions = Graph()
    additions.add((account, customer.name, first_name))
    removals = Graph()
    removals.add((account, customer.name, original_name))
    first.apply_change(
        additions=additions, removals=removals,
        actor_id="urn:uad:test:admin:first:it64-r4-s2",
        expected_versions={str(account): first_version},
    )
    expected = initial - removals + additions
    observer = CustomerRdfStore(repository_url, graph_iri)
    assert isomorphic(_normalized_strings(expected), _normalized_strings(observer.retrieve())), (
        "Prerequisite failed: the first administrator's update was not committed."
    )
    current_version = observer.get_resource_version(str(account))
    assert isinstance(current_version, str) and current_version != first_version, (
        "Changing the resource must change its persisted version token."
    )

    # This addition is still SHACL-conforming even after the first update.
    # Its rejection must therefore be a stale-version conflict, not validation.
    stale_additions = Graph()
    stale_additions.add((account, customer.label, stale_label))
    failure = None
    try:
        second.apply_change(
            additions=stale_additions, removals=Graph(),
            actor_id="urn:uad:test:admin:second:it64-r4-s2",
            expected_versions={str(account): second_version},
        )
    except Exception as error:
        failure = error

    try:
        actual = observer.retrieve()
        assert failure is not None, "IT-64R4S2 requires rejection of the stale update."
        assert getattr(failure, "code", None) == "stale_resource_version", (
            "The caller must receive an identifiable stale_resource_version conflict."
        )
        assert getattr(failure, "resource_iri", None) == str(account)
        assert getattr(failure, "expected_version", None) == second_version
        assert getattr(failure, "actual_version", None) == current_version
        assert getattr(failure, "refresh_required", None) is True, (
            "The conflict must indicate that the resource must be refreshed before retrying."
        )
        assert isomorphic(_normalized_strings(expected), _normalized_strings(actual)), (
            "The first administrator's committed graph must remain unchanged; "
            "none of the stale update may be persisted."
        )
        assert observer.get_resource_version(str(account)) == current_version, (
            "Rejecting a stale update must not advance the persisted resource version."
        )
    finally:
        close = getattr(failure, "close", None)
        if callable(close):
            close()
