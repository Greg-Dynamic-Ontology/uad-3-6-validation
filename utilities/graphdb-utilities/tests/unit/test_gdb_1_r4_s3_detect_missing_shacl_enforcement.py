"""GDB-1R4S3: Detect acceptance of RDF that violates an active shape.

A stateful HTTP double advertises the installed SHACL configuration but accepts
invalid RDF. No live server is contacted or repository modified.
"""

from hashlib import sha256
from io import BytesIO
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest
from rdflib import BNode, Graph, Literal, Namespace, RDF, URIRef, XSD
from rdflib.collection import Collection
from rdflib.compare import isomorphic

from owb_graphdb.client import GraphDBClient
from owb_graphdb.configuration import RepositoryConfiguration
from owb_graphdb.errors import RepositoryVerificationError
from owb_graphdb.validation import verify_nonconforming_dataset

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


def test_gdb_1_r4_s3_detect_missing_shacl_enforcement(monkeypatch):
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

    invalid = Graph().parse(FIXTURES / "nonconforming-data.ttl", format="turtle")
    dataset = Graph()
    focus = EX["verification-invalid"]
    for subject, predicate, obj in invalid:
        dataset.add((focus if subject == EX["record-001"] else subject, predicate, obj))
    assert (focus, RDF.type, EX.TestRecord) in dataset
    assert not list(dataset.objects(focus, EX.identifier))
    assert (EX.TestRecordShape, SH.targetClass, EX.TestRecord) in shapes
    assert any(
        (prop, SH.path, EX.identifier) in shapes
        and any(int(count) >= 1 for count in shapes.objects(prop, SH.minCount))
        for prop in shapes.objects(EX.TestRecordShape, SH.property)
    ), "The installed active shape must require the missing identifier."
    events = []
    accepted = []

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
            return BytesIO(stored[iri].serialize(format="turtle", encoding="utf-8"))
        assert iri == VERIFICATION_GRAPH, "Verification must not write other graphs."
        if method == "POST":
            # Deliberately broken enforcement: commit the supplied invalid RDF.
            incoming = Graph().parse(data=request.data, format="turtle")
            for triple in incoming:
                stored[iri].add(triple)
            accepted.append(_copy(stored[iri]))
            events.append("accepted")
            return BytesIO(b"")
        if method == "DELETE":
            assert stored[iri], "Cleanup must remove actually committed verification RDF."
            stored[iri] = Graph()
            events.append("cleaned")
            return BytesIO(b"")
        raise AssertionError(f"Unexpected request: {method} {parsed.path}")

    monkeypatch.setattr("owb_graphdb.client.urlopen", fake_urlopen)
    outcome = None
    with pytest.raises(RepositoryVerificationError) as failure:
        outcome = verify_nonconforming_dataset(
            client=GraphDBClient(server_url=SERVER_URL, timeout_seconds=1),
            configuration=configuration,
            dataset=dataset,
            verification_graph_iri=str(VERIFICATION_GRAPH),
        )

    assert accepted and _equivalent(dataset, accepted[0]), (
        "The setup must exercise successful acceptance of the nonconforming dataset."
    )
    message = str(failure.value).lower()
    assert all(word in message for word in ("expected", "shacl", "rejection", "did not occur")), message
    assert events == ["accepted", "cleaned"]
    assert not stored[VERIFICATION_GRAPH], "Verification RDF must be removed."
    assert outcome is None, "Failed verification must not return success or repository readiness."
    for iri, original in before.items():
        assert _equivalent(original, stored[iri]), f"Verification changed pre-existing RDF in {iri}."
