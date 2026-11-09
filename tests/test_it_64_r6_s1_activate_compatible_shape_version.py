"""IT-64R6S1: activate a compatible SHACL shape version."""

import os
from pathlib import Path
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
            shapes_version="it64-r6-s1-test-v1",
            data_graph_iris=("urn:uad:test:it64:r6:s1:customer",),
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


def test_it_64_r6_s1_activate_compatible_shape_version(request, tmp_path):
    assert callable(getattr(CustomerRdfStore, "activate_shape_version", None)), (
        "IT-64R6S1 requires activate_shape_version(shapes_path=..., version=...) "
        "to activate approved compatible shapes and identify their active version."
    )
    repository_url = request.getfixturevalue("customer_test_repository_url")
    graph_iri = "urn:uad:test:it64:r6:s1:customer"
    customer = Namespace("urn:uad:customer:")
    sh = Namespace("http://www.w3.org/ns/shacl#")
    meta = Namespace("urn:owb:graphdb:shape-set:")
    shape_set = URIRef("urn:owb:graphdb:installed-shape-set")
    metadata_graph = "urn:owb:graphdb:shape-set-metadata"
    shapes_graph = "urn:owb:graphdb:shapes"
    account = URIRef("urn:uad:test:account:it64-r6-s1")
    user = URIRef("urn:uad:test:user:it64-r6-s1")
    membership = URIRef("urn:uad:test:membership:it64-r6-s1")
    initial = Graph()
    initial.add((account, RDF.type, customer.CustomerAccount))
    initial.add((account, customer.name, Literal("Compatible account", datatype=XSD.string)))
    initial.add((account, customer.createdAt, Literal(
        "2026-11-05T12:00:00Z", datatype=XSD.dateTime,
    )))
    initial.add((user, RDF.type, customer.User))
    initial.add((membership, RDF.type, customer.Membership))
    initial.add((membership, customer.account, account))
    initial.add((membership, customer.user, user))
    initial.add((membership, customer.role, customer.Owner))
    store = CustomerRdfStore(repository_url, graph_iri)
    store.commit(initial, actor_id="urn:uad:test:system:it64-r6-s1")
    before = _read_graph(repository_url, graph_iri)
    assert isomorphic(_normalized_strings(initial), _normalized_strings(before))

    # The approved candidate adds a constraint satisfied by existing customer
    # names. Approval is a scenario prerequisite, not an authorization bypass.
    candidate = Graph().parse(data=TEST_SHAPES, format="turtle")
    name_shapes = list(candidate.subjects(sh.path, customer.name))
    assert len(name_shapes) == 1
    candidate.add((name_shapes[0], sh.maxLength, Literal(40)))
    candidate_path = tmp_path / "approved-customer-shapes-v2.ttl"
    candidate.serialize(destination=str(candidate_path), format="turtle", encoding="utf-8")
    new_version = "it64-r6-s1-test-v2"
    store.activate_shape_version(shapes_path=candidate_path, version=new_version)

    metadata = _read_graph(repository_url, metadata_graph)
    versions = list(metadata.objects(shape_set, meta.version))
    assert len(versions) == 1 and str(versions[0]) == new_version, (
        "The active shape version must be identifiable through persisted metadata."
    )
    installed = _read_graph(repository_url, shapes_graph)
    assert isomorphic(candidate, installed), "The proposed shape graph must actually be installed."
    assert isomorphic(_normalized_strings(before), _normalized_strings(store.retrieve())), (
        "Activating compatible shapes must preserve existing customer RDF."
    )

    conforming = Graph()
    for triple in before:
        conforming.add(triple)
    conforming.set((account, customer.name, Literal("Updated account", datatype=XSD.string)))
    store.commit(conforming, actor_id="urn:uad:test:system:it64-r6-s1")
    assert isomorphic(_normalized_strings(conforming), _normalized_strings(store.retrieve()))

    invalid = Graph()
    for triple in conforming:
        invalid.add(triple)
    invalid.set((account, customer.name, Literal("X" * 41, datatype=XSD.string)))
    failure = None
    try:
        store.commit(invalid, actor_id="urn:uad:test:system:it64-r6-s1")
    except Exception as error:
        failure = error
    try:
        assert failure is not None, "The newly activated maxLength constraint must reject this commit."
        report = getattr(failure, "validation_report", None)
        assert isinstance(report, Graph), "Expected a SHACL rejection, not an unrelated error."
        assert any(
            (node, sh.conforms, Literal(False)) in report
            for node in report.subjects(RDF.type, sh.ValidationReport)
        )
        assert any(
            (result, sh.focusNode, account) in report
            and (result, sh.resultPath, customer.name) in report
            for result in report.subjects(sh.sourceConstraintComponent, sh.MaxLengthConstraintComponent)
        ), "The report must identify the newly activated name maxLength constraint."
        assert isomorphic(_normalized_strings(conforming), _normalized_strings(store.retrieve())), (
            "The rejected write must leave the last conforming dataset intact."
        )
        versions = list(_read_graph(repository_url, metadata_graph).objects(shape_set, meta.version))
        assert len(versions) == 1 and str(versions[0]) == new_version
    finally:
        close = getattr(failure, "close", None)
        if callable(close):
            close()
