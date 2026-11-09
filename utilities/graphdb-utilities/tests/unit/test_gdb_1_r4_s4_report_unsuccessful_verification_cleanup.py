"""GDB-1R4S4: Return a failure result identifying unsuccessful cleanup.

A stateful HTTP double advertises the installed SHACL configuration and accepts
conforming RDF, then refuses cleanup. No live server is contacted.
"""

from hashlib import sha256
from io import BytesIO
from urllib.error import HTTPError
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest
from rdflib import BNode, Graph, Literal, Namespace, RDF, URIRef, XSD
from rdflib.collection import Collection
from rdflib.compare import isomorphic

from owb_graphdb.client import GraphDBClient
from owb_graphdb.configuration import RepositoryConfiguration
from owb_graphdb.errors import GraphDBError
from owb_graphdb.validation import verify_conforming_dataset

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
SERVER_URL = "http://127.0.0.1:7200"
REPOSITORY_ID = "owb-graphdb-test"
DATA_GRAPH = URIRef("urn:owb:graphdb:test:existing-data")
VERIFICATION_GRAPH = URIRef("urn:owb:graphdb:test:verification")
SHAPES_GRAPH = URIRef("urn:owb:graphdb:shapes")
MAPPING_GRAPH = URIRef("http://rdf4j.org/schema/rdf4j#SHACLShapeGraph")
METADATA_GRAPH = URIRef("urn:owb:graphdb:shape-set-metadata")
SHAPE_SET = URIRef("urn:owb:graphdb:installed-shape-set")
META = Namespace("urn:owb:graphdb:shape-set:")
SH = Namespace("http://www.w3.org/ns/shacl#")
EX = Namespace("https://example.org/graphdb-utilities/test/")


def _copy(graph):
    result = Graph()
    for triple in graph:
        result.add(triple)
    return result


def _equivalent(left, right):
    def normalize(graph):
        result = Graph()
        for subject, predicate, obj in graph:
            if isinstance(obj, Literal) and obj.datatype is None and obj.language is None:
                obj = Literal(str(obj), datatype=XSD.string)
            result.add((subject, predicate, obj))
        return result
    return isomorphic(normalize(left), normalize(right))


def test_gdb_1_r4_s4_report_unsuccessful_verification_cleanup(monkeypatch):
    configuration = RepositoryConfiguration(
        server_url=SERVER_URL,
        repository_id=REPOSITORY_ID,
        repository_config_path=FIXTURES / "repository-config.ttl",
        shapes_path=FIXTURES / "shapes.ttl",
        shapes_version="1.0.0",
        data_graph_iris=(str(DATA_GRAPH), str(VERIFICATION_GRAPH)),
    )
    shape_bytes = configuration.shapes_path.read_bytes()
    shapes = Graph().parse(data=shape_bytes, format="turtle")
    metadata = Graph()
    metadata.add((SHAPE_SET, RDF.type, META.InstalledShapeSet))
    metadata.add((SHAPE_SET, META.shapesGraph, SHAPES_GRAPH))
    metadata.add((SHAPE_SET, META.version, Literal("1.0.0", datatype=XSD.string)))
    metadata.add((SHAPE_SET, META.contentDigest, Literal(sha256(shape_bytes).hexdigest(), datatype=XSD.string)))
    head = BNode()
    metadata.add((SHAPE_SET, META.dataGraphs, head))
    Collection(metadata, head, [DATA_GRAPH, VERIFICATION_GRAPH])
    mappings = Graph()
    for iri in (DATA_GRAPH, VERIFICATION_GRAPH):
        mappings.add((iri, SH.shapesGraph, SHAPES_GRAPH))
    stored = {
        SHAPES_GRAPH: shapes,
        METADATA_GRAPH: metadata,
        MAPPING_GRAPH: mappings,
        DATA_GRAPH: Graph().parse(FIXTURES / "conforming-data.ttl", format="turtle"),
        VERIFICATION_GRAPH: Graph(),
    }
    before = {iri: _copy(graph) for iri, graph in stored.items()}
    assert before[DATA_GRAPH]
    config_bytes = configuration.repository_config_path.read_bytes()

    dataset = Graph().parse(FIXTURES / "conforming-data.ttl", format="turtle")
    # Distinct resource identity from the pre-existing data graph.
    supplied = Graph()
    for subject, predicate, obj in dataset:
        supplied.add((EX["cleanup-check"] if subject == EX["record-001"] else subject, predicate, obj))
    assert supplied
    events = []
    committed = []

    def fake_urlopen(request, timeout=None):
        method = request.get_method()
        parsed = urlsplit(request.full_url)
        assert parsed.netloc == "127.0.0.1:7200"
        if method == "GET" and parsed.path == f"/rest/repositories/{REPOSITORY_ID}":
            return BytesIO(config_bytes)
        assert parsed.path == f"/repositories/{REPOSITORY_ID}/statements", (
            f"Unexpected request: {method} {parsed.path}"
        )
        contexts = parse_qs(parsed.query).get("context", [])
        assert len(contexts) == 1
        iri = URIRef(contexts[0].removeprefix("<").removesuffix(">"))
        assert iri in stored
        if method == "GET":
            if iri == VERIFICATION_GRAPH and stored[iri]:
                events.append("read-back")
            return BytesIO(stored[iri].serialize(format="turtle", encoding="utf-8"))
        assert iri == VERIFICATION_GRAPH, "Verification must not write other graphs."
        if method == "POST":
            incoming = Graph().parse(data=request.data, format="turtle")
            for triple in incoming:
                stored[iri].add(triple)
            committed.append(_copy(stored[iri]))
            events.append("committed")
            return BytesIO(b"")
        if method == "DELETE":
            assert _equivalent(supplied, stored[iri]), (
                "Cleanup must fail only after the verification data was written."
            )
            events.append("cleanup-failed")
            raise HTTPError(
                request.full_url, 500, "Simulated cleanup failure", {},
                BytesIO(b"The verification graph could not be cleared."),
            )
        raise AssertionError(f"Unexpected request: {method} {parsed.path}")

    monkeypatch.setattr("owb_graphdb.client.urlopen", fake_urlopen)
    result = None
    raised = None
    try:
        result = verify_conforming_dataset(
            client=GraphDBClient(server_url=SERVER_URL, timeout_seconds=1),
            configuration=configuration,
            dataset=supplied,
            verification_graph_iri=str(VERIFICATION_GRAPH),
        )
    except GraphDBError as error:
        # Inspect the fixture state before reporting the intended contract RED.
        raised = error

    assert committed and _equivalent(supplied, committed[0])
    assert "read-back" in events
    assert "cleanup-failed" in events
    assert events.index("committed") < events.index("read-back") < events.index("cleanup-failed")
    assert _equivalent(supplied, stored[VERIFICATION_GRAPH]), (
        "The failed cleanup must leave verification RDF requiring operator attention."
    )
    for iri, original in before.items():
        if iri != VERIFICATION_GRAPH:
            assert _equivalent(original, stored[iri]), f"Pre-existing RDF changed in {iri}."

    assert raised is None, (
        "GDB-1R4S4 requires a returned failure result when cleanup fails, "
        f"but verification raised {type(raised).__name__}: {raised}"
    )
    assert result is not None, "Cleanup failure must return an explicit failure result."
    assert result.success is False
    assert result.ready is False, "A repository with failed verification must not be reported ready."
    assert str(VERIFICATION_GRAPH) in result.message, (
        "The failure result must identify the graph requiring cleanup."
    )
    message = result.message.lower()
    assert "cleanup" in message and any(word in message for word in ("fail", "could not")), result.message
