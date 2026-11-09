"""GDB-1R3S3: Reject a different installed shape set without writes."""

from hashlib import sha256
from io import BytesIO
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest
from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.collection import Collection
from rdflib.compare import isomorphic
from rdflib.namespace import RDF, RDFS, XSD

from owb_graphdb.client import GraphDBClient
from owb_graphdb.configuration import RepositoryConfiguration
from owb_graphdb.setup import setup_repository

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
SERVER_URL = "http://127.0.0.1:7200"
REPOSITORY_ID = "owb-graphdb-test"
DATA_GRAPH = URIRef("urn:owb:graphdb:test:data")
SHAPES_GRAPH = URIRef("urn:owb:graphdb:shapes")
MAPPING_GRAPH = URIRef("http://rdf4j.org/schema/rdf4j#SHACLShapeGraph")
METADATA_GRAPH = URIRef("urn:owb:graphdb:shape-set-metadata")
SHAPE_SET = URIRef("urn:owb:graphdb:installed-shape-set")
META = Namespace("urn:owb:graphdb:shape-set:")
SH = Namespace("http://www.w3.org/ns/shacl#")


@pytest.mark.parametrize("mismatch", ["version", "digest", "both"])
def test_gdb_1_r3_s3_detect_different_installed_shape_set(monkeypatch, mismatch):
    configuration = RepositoryConfiguration(
        server_url=SERVER_URL,
        repository_id=REPOSITORY_ID,
        repository_config_path=FIXTURES / "repository-config.ttl",
        shapes_path=FIXTURES / "shapes.ttl",
        shapes_version="2.0.0",
        data_graph_iris=(str(DATA_GRAPH),),
    )
    supplied = configuration.shapes_path.read_bytes()
    installed_shapes = Graph().parse(data=supplied, format="turtle")
    installed_bytes = supplied
    if mismatch in {"digest", "both"}:
        # Persist genuinely different RDF, with a digest of those exact bytes.
        installed_shapes.add((
            URIRef("urn:owb:graphdb:test:previous-release"),
            RDFS.comment,
            Literal("Previously installed application shape release"),
        ))
        installed_bytes = installed_shapes.serialize(format="turtle").encode("utf-8")
    installed_version = "1.0.0" if mismatch in {"version", "both"} else "2.0.0"
    installed_digest = sha256(installed_bytes).hexdigest()
    assert (installed_version != configuration.shapes_version) == (mismatch != "digest")
    assert (installed_digest != sha256(supplied).hexdigest()) == (mismatch != "version")

    metadata = Graph()
    metadata.add((SHAPE_SET, RDF.type, META.InstalledShapeSet))
    metadata.add((SHAPE_SET, META.shapesGraph, SHAPES_GRAPH))
    metadata.add((SHAPE_SET, META.version, Literal(installed_version, datatype=XSD.string)))
    metadata.add((SHAPE_SET, META.contentDigest, Literal(installed_digest, datatype=XSD.string)))
    head = BNode()
    metadata.add((SHAPE_SET, META.dataGraphs, head))
    Collection(metadata, head, [DATA_GRAPH])
    mappings = Graph()
    mappings.add((DATA_GRAPH, SH.shapesGraph, SHAPES_GRAPH))
    data = Graph().parse(FIXTURES / "conforming-data.ttl", format="turtle")
    assert len(data) > 0 and len(installed_shapes) > 0

    stored = {
        SHAPES_GRAPH: installed_bytes,
        METADATA_GRAPH: metadata.serialize(format="turtle").encode("utf-8"),
        MAPPING_GRAPH: mappings.serialize(format="turtle").encode("utf-8"),
        DATA_GRAPH: data.serialize(format="turtle").encode("utf-8"),
    }
    before = {
        iri: Graph().parse(data=content, format="turtle")
        for iri, content in stored.items()
    }
    configuration_bytes = configuration.repository_config_path.read_bytes()
    requests = []

    def fake_urlopen(request, timeout=None):
        method = request.get_method()
        url = request.full_url
        requests.append((method, url))
        assert method == "GET", f"Setup must not upgrade, replace, or write: {method} {url}"
        parsed = urlsplit(url)
        assert parsed.netloc == "127.0.0.1:7200"
        if parsed.path == "/rest/repositories":
            return BytesIO(b'[{"id":"owb-graphdb-test"}]')
        if parsed.path == f"/rest/repositories/{REPOSITORY_ID}":
            return BytesIO(configuration_bytes)
        if parsed.path == f"/repositories/{REPOSITORY_ID}/statements":
            context = parse_qs(parsed.query).get("context")
            assert context is not None and len(context) == 1
            iri = URIRef(context[0].removeprefix("<").removesuffix(">"))
            assert iri in stored, f"Unexpected graph: {iri}"
            return BytesIO(stored[iri])
        raise AssertionError(f"Unexpected GraphDB request: {method} {url}")

    monkeypatch.setattr("owb_graphdb.client.urlopen", fake_urlopen)
    result = setup_repository(
        client=GraphDBClient(server_url=SERVER_URL, timeout_seconds=1),
        configuration=configuration,
    )

    assert result is not None, "Setup must return a failure result."
    assert result.success is False
    assert result.ready is False
    assert REPOSITORY_ID in result.message
    message = result.message.lower()
    assert "shape" in message
    assert any(word in message for word in ("differs", "different", "mismatch")), result.message
    if mismatch == "version":
        assert "version" in message, result.message
    elif mismatch == "digest":
        assert "digest" in message, result.message

    # Check attempted writes as well as stored content: replacing and restoring
    # the original shapes would still violate this scenario.
    assert requests and all(method == "GET" for method, _ in requests), requests
    for iri, expected in before.items():
        after = Graph().parse(data=stored[iri], format="turtle")
        assert isomorphic(expected, after), f"Setup changed {iri}"
