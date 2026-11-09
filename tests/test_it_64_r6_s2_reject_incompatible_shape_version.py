"""IT-64R6S2: reject an incompatible SHACL shape version."""

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
            shapes_version="it64-r6-s2-test-v1",
            data_graph_iris=("urn:uad:test:it64:r6:s2:customer",),
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


def _assert_violation(error, focus, path, constraint):
    sh = Namespace("http://www.w3.org/ns/shacl#")
    assert error is not None, "Expected SHACL rejection, but the operation succeeded."
    report = getattr(error, "validation_report", None)
    assert isinstance(report, Graph), (
        f"Expected a SHACL validation report, not an unrelated {type(error).__name__}."
    )
    assert any(
        (node, sh.conforms, Literal(False)) in report
        for node in report.subjects(RDF.type, sh.ValidationReport)
    )
    assert any(
        (result, sh.focusNode, focus) in report and (result, sh.resultPath, path) in report
        for result in report.subjects(sh.sourceConstraintComponent, constraint)
    ), "The report must identify the actual resource, property, and violated constraint."


def test_it_64_r6_s2_reject_incompatible_shape_version(customer_test_repository_url, tmp_path):
    repository_url = customer_test_repository_url
    graph_iri = "urn:uad:test:it64:r6:s2:customer"
    customer = Namespace("urn:uad:customer:")
    sh = Namespace("http://www.w3.org/ns/shacl#")
    account = URIRef("urn:uad:test:account:it64-r6-s2")
    user = URIRef("urn:uad:test:user:it64-r6-s2")
    membership = URIRef("urn:uad:test:membership:it64-r6-s2")
    initial = Graph()
    initial.add((account, RDF.type, customer.CustomerAccount))
    initial.add((account, customer.name, Literal("Existing customer account", datatype=XSD.string)))
    initial.add((account, customer.createdAt, Literal(
        "2026-11-05T12:00:00Z", datatype=XSD.dateTime,
    )))
    initial.add((user, RDF.type, customer.User))
    initial.add((membership, RDF.type, customer.Membership))
    initial.add((membership, customer.account, account))
    initial.add((membership, customer.user, user))
    initial.add((membership, customer.role, customer.Owner))
    store = CustomerRdfStore(repository_url, graph_iri)
    store.commit(initial, actor_id="urn:uad:test:system:it64-r6-s2")
    observed_graphs = (
        graph_iri,
        "urn:owb:graphdb:shapes",
        "urn:owb:graphdb:shape-set-metadata",
        "http://rdf4j.org/schema/rdf4j#SHACLShapeGraph",
        PROVENANCE_GRAPH,
    )
    before = {iri: _read_graph(repository_url, iri) for iri in observed_graphs}
    assert isomorphic(_normalized_strings(initial), _normalized_strings(before[graph_iri]))

    candidate = Graph().parse(data=TEST_SHAPES, format="turtle")
    name_shapes = list(candidate.subjects(sh.path, customer.name))
    assert len(name_shapes) == 1
    candidate.add((name_shapes[0], sh.maxLength, Literal(5)))
    path = tmp_path / "incompatible-customer-shapes-v2.ttl"
    candidate.serialize(destination=str(path), format="turtle", encoding="utf-8")
    failure = None
    try:
        store.activate_shape_version(shapes_path=path, version="it64-r6-s2-test-v2")
    except Exception as error:
        failure = error
    try:
        _assert_violation(failure, account, customer.name, sh.MaxLengthConstraintComponent)
        for iri, original in before.items():
            actual = _read_graph(repository_url, iri)
            assert isomorphic(_normalized_strings(original), _normalized_strings(actual)), (
                f"IT-64R6S2: rejected activation changed graph {iri}."
            )
    finally:
        close = getattr(failure, "close", None)
        if callable(close):
            close()

    # Prove the old version remains operational: this name exceeds the rejected
    # five-character limit but is valid under the original installed shapes.
    allowed = Graph()
    for triple in initial:
        allowed.add(triple)
    allowed.set((account, customer.name, Literal("Still allowed by original shapes", datatype=XSD.string)))
    store.commit(allowed, actor_id="urn:uad:test:system:it64-r6-s2")
    assert isomorphic(_normalized_strings(allowed), _normalized_strings(store.retrieve()))

    # Also prove validation was not disabled during the unsuccessful upgrade.
    invalid = Graph()
    for triple in allowed:
        invalid.add(triple)
    invalid.remove((account, customer.name, None))
    failure = None
    try:
        store.commit(invalid, actor_id="urn:uad:test:system:it64-r6-s2")
    except Exception as error:
        failure = error
    try:
        _assert_violation(failure, account, customer.name, sh.MinCountConstraintComponent)
        assert isomorphic(_normalized_strings(allowed), _normalized_strings(store.retrieve()))
        for iri in observed_graphs[1:4]:
            assert isomorphic(
                _normalized_strings(before[iri]), _normalized_strings(_read_graph(repository_url, iri)),
            ), "The original shapes, version metadata, and mappings must remain active."
    finally:
        close = getattr(failure, "close", None)
        if callable(close):
            close()
