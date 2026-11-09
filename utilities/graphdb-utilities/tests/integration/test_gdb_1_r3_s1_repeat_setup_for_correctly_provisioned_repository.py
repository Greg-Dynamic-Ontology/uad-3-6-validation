"""GDB-1R3S1: Repeated setup preserves a provisioned repository."""

import hashlib
import json
import os
from pathlib import Path
from urllib.parse import urlencode
from uuid import uuid4

from rdflib import Graph, Literal, Namespace
from rdflib.compare import isomorphic
from rdflib.namespace import XSD

from owb_graphdb.client import GraphDBClient
from owb_graphdb.configuration import RepositoryConfiguration
from owb_graphdb.setup import setup_repository
from owb_graphdb.shapes import retrieve_shape_set


FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
REP = Namespace("http://www.openrdf.org/config/repository#")

TEST_PREFIX = "owb-gdb-1"
DATA_GRAPH = "https://example.org/graphdb-utilities/test/data"
SHAPES_GRAPH = "urn:owb:graphdb:shapes"
MAPPING_GRAPH = "http://rdf4j.org/schema/rdf4j#SHACLShapeGraph"
METADATA_GRAPH = "urn:owb:graphdb:shape-set-metadata"
SHAPES_VERSION = "1.0.0"


class RecordingClient(GraphDBClient):
    """Record requests while communicating with the real GraphDB server."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.requests = []

    def request(self, *, method, path, **kwargs):
        self.requests.append((method.upper(), path))
        return super().request(method=method, path=path, **kwargs)


def _normalized(graph: Graph) -> Graph:
    """Treat plain strings and xsd:string as equivalent RDF 1.1 literals."""
    result = Graph()
    for subject, predicate, obj in graph:
        if (
            isinstance(obj, Literal)
            and obj.datatype is None
            and obj.language is None
        ):
            obj = Literal(str(obj), datatype=XSD.string)
        result.add((subject, predicate, obj))
    return result


def _assert_equivalent(before: Graph, after: Graph, description: str):
    assert isomorphic(_normalized(before), _normalized(after)), (
        f"{description} changed during repeated setup."
    )


def _read_graph(client, repository_id, graph_iri):
    query = urlencode({
        "context": f"<{graph_iri}>",
        "infer": "false",
    })
    content = client.request(
        method="GET",
        path=f"/repositories/{repository_id}/statements?{query}",
        accept="text/turtle",
    )
    return Graph().parse(data=content, format="turtle")


def _read_configuration(client, repository_id):
    content = client.request(
        method="GET",
        path=f"/rest/repositories/{repository_id}",
        accept="text/turtle",
    )
    return Graph().parse(data=content, format="turtle")


def _remove_previous_test_repositories(client):
    """Delete only repositories in the expressly reserved test namespace."""
    content = client.request(
        method="GET",
        path="/rest/repositories",
        accept="application/json",
    )
    for repository in json.loads(content):
        repository_id = repository["id"]
        if repository_id.startswith(TEST_PREFIX):
            client.request(
                method="DELETE",
                path=f"/rest/repositories/{repository_id}",
            )


def _write_repository_configuration(tmp_path, repository_id):
    graph = Graph().parse(
        FIXTURES / "repository-config.ttl",
        format="turtle",
    )
    subjects = list(graph.subjects(REP.repositoryID, None))
    assert len(subjects) == 1, (
        "The configuration fixture must identify exactly one repository."
    )
    graph.set((subjects[0], REP.repositoryID, Literal(repository_id)))

    path = tmp_path / "repository-config.ttl"
    graph.serialize(destination=str(path), format="turtle")
    return path


def test_gdb_1_r3_s1_repeat_setup_for_correctly_provisioned_repository(
    tmp_path,
):
    server_url = os.environ.get(
        "GRAPHDB_TEST_SERVER_URL",
        "http://localhost:7200",
    )
    headers = {}
    authorization = os.environ.get("GRAPHDB_AUTHORIZATION")
    if authorization:
        headers["Authorization"] = authorization

    client = GraphDBClient(
        server_url=server_url,
        headers=headers,
        timeout_seconds=30,
    )

    # Reserved test repositories only; owb-gdb-dev and MISMO are untouched.
    _remove_previous_test_repositories(client)

    repository_id = f"{TEST_PREFIX}-r3-s1-{uuid4().hex}"
    shapes_path = FIXTURES / "shapes.ttl"

    configuration = RepositoryConfiguration(
        server_url=server_url,
        repository_id=repository_id,
        repository_config_path=_write_repository_configuration(
            tmp_path,
            repository_id,
        ),
        shapes_path=shapes_path,
        shapes_version=SHAPES_VERSION,
        data_graph_iris=(DATA_GRAPH,),
    )

    # Given a correctly provisioned repository.
    initial_result = setup_repository(
        client=client,
        configuration=configuration,
    )
    assert initial_result is not None
    assert initial_result.success, initial_result.message
    assert initial_result.ready, initial_result.message

    expected_digest = hashlib.sha256(shapes_path.read_bytes()).hexdigest()
    installed = retrieve_shape_set(
        client=client,
        configuration=configuration,
    )
    assert installed.version == SHAPES_VERSION
    assert installed.content_digest == expected_digest
    assert installed.data_graph_iris == (DATA_GRAPH,)

    supplied_shapes = Graph().parse(shapes_path, format="turtle")
    _assert_equivalent(
        supplied_shapes,
        installed.graph,
        "Initial installed shapes",
    )

    # Seed actual data so preservation cannot pass on an empty graph.
    data_path = FIXTURES / "conforming-data.ttl"
    query = urlencode({"context": f"<{DATA_GRAPH}>"})
    client.request(
        method="POST",
        path=f"/repositories/{repository_id}/statements?{query}",
        body=data_path.read_bytes(),
        content_type="text/turtle",
    )

    graph_iris = (
        DATA_GRAPH,
        SHAPES_GRAPH,
        MAPPING_GRAPH,
        METADATA_GRAPH,
    )
    before = {
        iri: _read_graph(client, repository_id, iri)
        for iri in graph_iris
    }
    assert len(before[DATA_GRAPH]) > 0
    assert len(before[SHAPES_GRAPH]) > 0
    assert len(before[METADATA_GRAPH]) > 0

    _assert_equivalent(
        Graph().parse(data_path, format="turtle"),
        before[DATA_GRAPH],
        "Seeded data",
    )
    configuration_before = _read_configuration(client, repository_id)

    # When setup runs again against the same repository and shape set.
    repeat_client = RecordingClient(
        server_url=server_url,
        headers=headers,
        timeout_seconds=30,
    )
    result = setup_repository(
        client=repeat_client,
        configuration=configuration,
    )

    # Then setup succeeds and reports readiness.
    assert result is not None, "Repeated setup must return a result."
    assert result.success, result.message
    assert result.ready, result.message

    # Recreating the repository and restoring its contents is not acceptable.
    repository_endpoints = {
        "/rest/repositories",
        f"/rest/repositories/{repository_id}",
        f"/repositories/{repository_id}",
    }
    replacement_requests = [
        (method, path)
        for method, path in repeat_client.requests
        if method in {"DELETE", "POST", "PUT"}
        and path.split("?", 1)[0].rstrip("/") in repository_endpoints
    ]
    assert not replacement_requests, (
        "Repeated setup must not delete, recreate, or replace the repository: "
        f"{replacement_requests}"
    )

    # Inspect only this test's repository.
    descriptions = {
        DATA_GRAPH: "Existing RDF data",
        SHAPES_GRAPH: "Installed shapes",
        MAPPING_GRAPH: "SHACL data-graph scope",
        METADATA_GRAPH: "Setup metadata",
    }
    for iri in graph_iris:
        after = _read_graph(client, repository_id, iri)
        _assert_equivalent(before[iri], after, descriptions[iri])

    _assert_equivalent(
        configuration_before,
        _read_configuration(client, repository_id),
        "Repository configuration",
    )

    # Metadata equivalence above also rejects extra blank-node list structures.
    installed_after = retrieve_shape_set(
        client=client,
        configuration=configuration,
    )
    assert installed_after.version == SHAPES_VERSION
    assert installed_after.content_digest == expected_digest
    assert installed_after.data_graph_iris == (DATA_GRAPH,)