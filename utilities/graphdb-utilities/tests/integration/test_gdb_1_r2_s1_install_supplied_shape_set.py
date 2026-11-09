"""GDB-1R2S1: Install the supplied shape set."""

import hashlib
import json
import os
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen
from uuid import uuid4

import pytest
from rdflib import Graph, Literal, Namespace, RDF, XSD
from rdflib.compare import graph_diff, isomorphic, to_isomorphic

from owb_graphdb.client import GraphDBClient
from owb_graphdb.configuration import RepositoryConfiguration
from owb_graphdb.provisioning import provision_repository
from owb_graphdb.shapes import install_shape_set, retrieve_shape_set


FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"

REP = Namespace("http://www.openrdf.org/config/repository#")
SAIL = Namespace("http://www.openrdf.org/config/sail#")
SHACL_CONFIG = Namespace("http://rdf4j.org/config/sail/shacl#")

SHAPES_GRAPH = "http://rdf4j.org/schema/rdf4j#SHACLShapeGraph"
DATA_GRAPH = "https://example.org/graphdb-utilities/test/data"
TEST_PREFIX = "owb-gdb-1"


def _request(
    server_url,
    headers,
    method,
    path,
    *,
    body=None,
    content_type=None,
    accept=None,
):
    """Use HTTP directly for independent test observations."""
    request_headers = dict(headers)
    if content_type:
        request_headers["Content-Type"] = content_type
    if accept:
        request_headers["Accept"] = accept

    request = Request(
        f"{server_url}{path}",
        data=body,
        headers=request_headers,
        method=method,
    )
    with urlopen(request, timeout=30) as response:
        return response.read()


def _repository_ids(server_url, headers):
    payload = _request(
        server_url,
        headers,
        "GET",
        "/rest/repositories",
        accept="application/json",
    )
    return {item["id"] for item in json.loads(payload)}


def _cleanup_test_repositories(server_url, headers):
    """Delete only repositories matching the authorized test prefix."""
    before = _repository_ids(server_url, headers)
    disposable = {
        repository_id
        for repository_id in before
        if repository_id.startswith(TEST_PREFIX)
    }

    for repository_id in sorted(disposable):
        _request(
            server_url,
            headers,
            "DELETE",
            f"/rest/repositories/{quote(repository_id, safe='')}",
        )

    assert _repository_ids(server_url, headers) == before - disposable


def _graph_path(repository_id, graph_iri, *, explicit_only=False):
    parameters = {"context": f"<{graph_iri}>"}
    if explicit_only:
        parameters["infer"] = "false"

    return (
        f"/repositories/{quote(repository_id, safe='')}"
        f"/statements?{urlencode(parameters)}"
    )


def _read_graph(server_url, headers, repository_id, graph_iri):
    """Read explicit statements from one graph in this test's repository."""
    payload = _request(
        server_url,
        headers,
        "GET",
        _graph_path(repository_id, graph_iri, explicit_only=True),
        accept="text/turtle",
    )
    graph = Graph()
    if payload.strip():
        graph.parse(data=payload.decode("utf-8"), format="turtle")
    return graph


def _normalize_string_literals(graph):
    """Represent RDF 1.1 simple literals explicitly as xsd:string."""
    normalized = Graph()

    for subject, predicate, value in graph:
        if (
            isinstance(value, Literal)
            and value.datatype is None
            and value.language is None
        ):
            value = Literal(
                str(value),
                datatype=XSD.string,
                normalize=False,
            )
        normalized.add((subject, predicate, value))

    return normalized


def _assert_equivalent(actual, expected, description):
    """Compare RDF graphs without depending on blank-node labels."""
    actual = _normalize_string_literals(actual)
    expected = _normalize_string_literals(expected)

    if isomorphic(actual, expected):
        return

    _, unexpected, missing = graph_diff(
        to_isomorphic(actual),
        to_isomorphic(expected),
    )

    pytest.fail(
        f"{description} is not equivalent.\n"
        f"Actual triples: {len(actual)}; expected triples: {len(expected)}\n"
        "Missing triples:\n"
        f"{missing.serialize(format='turtle')}\n"
        "Unexpected triples:\n"
        f"{unexpected.serialize(format='turtle')}"
    )


def _assert_shacl_enabled(server_url, headers, repository_id):
    payload = _request(
        server_url,
        headers,
        "GET",
        f"/rest/repositories/{quote(repository_id, safe='')}",
        accept="text/turtle",
    )
    configuration = Graph().parse(
        data=payload.decode("utf-8"),
        format="turtle",
    )

    shacl_nodes = [
        subject
        for subject, value in configuration.subject_objects(SAIL.sailType)
        if str(value) == "rdf4j:ShaclSail"
    ]
    assert shacl_nodes, "Repository must use ShaclSail."

    assert any(
        str(value).strip().lower() in {"true", "1"}
        for node in shacl_nodes
        for value in configuration.objects(
            node,
            SHACL_CONFIG.validationEnabled,
        )
    ), "SHACL validation must be enabled."


def test_gdb_1_r2_s1_install_supplied_shape_set(tmp_path):
    server_url = os.environ.get(
        "GRAPHDB_TEST_SERVER_URL",
        "http://localhost:7200",
    ).rstrip("/")

    headers = {}
    authorization = os.environ.get("GRAPHDB_AUTHORIZATION")
    if authorization:
        headers["Authorization"] = authorization

    _cleanup_test_repositories(server_url, headers)
    repository_id = f"owb-gdb-1-r2-s1-{uuid4().hex}"

    repository_config = Graph().parse(
        FIXTURES / "repository-config.ttl",
        format="turtle",
    )
    repositories = list(
        repository_config.subjects(RDF.type, REP.Repository)
    )
    assert len(repositories) == 1

    repository_config.set(
        (repositories[0], REP.repositoryID, Literal(repository_id))
    )
    config_path = tmp_path / "repository-config.ttl"
    repository_config.serialize(
        destination=str(config_path),
        format="turtle",
    )

    shape_bytes = (FIXTURES / "shapes.ttl").read_bytes()
    shapes_path = tmp_path / "shapes.ttl"
    shapes_path.write_bytes(shape_bytes)

    expected_shapes = Graph().parse(
        data=shape_bytes.decode("utf-8"),
        format="turtle",
    )
    expected_digest = hashlib.sha256(shape_bytes).hexdigest()

    configuration = RepositoryConfiguration(
        server_url=server_url,
        repository_id=repository_id,
        repository_config_path=config_path,
        shapes_path=shapes_path,
        shapes_version="1.0.0",
        data_graph_iris=(DATA_GRAPH,),
    )
    client = GraphDBClient(
        server_url=server_url,
        headers=headers,
        timeout_seconds=30,
    )

    # Given an existing SHACL-enabled repository without shapes.
    provision_repository(client=client, configuration=configuration)
    assert repository_id in _repository_ids(server_url, headers)
    _assert_shacl_enabled(server_url, headers, repository_id)

    assert len(
        _read_graph(server_url, headers, repository_id, SHAPES_GRAPH)
    ) == 0

    # When the utility installs the supplied shape set.
    install_shape_set(client=client, configuration=configuration)

    # Retrieval must use persisted state, not the source file or client.
    shapes_path.unlink()
    reader = GraphDBClient(
        server_url=server_url,
        headers=headers,
        timeout_seconds=30,
    )
    installed = retrieve_shape_set(
        client=reader,
        configuration=configuration,
    )

    _assert_equivalent(
        installed.graph,
        expected_shapes,
        "Retrieved shape graph",
    )
    assert installed.version == "1.0.0"
    assert installed.content_digest == expected_digest
    assert installed.data_graph_iris == (DATA_GRAPH,)

    # Verify rejection before conforming data could mask missing fields.
    assert len(
        _read_graph(server_url, headers, repository_id, DATA_GRAPH)
    ) == 0

    with pytest.raises(HTTPError) as rejected:
        _request(
            server_url,
            headers,
            "POST",
            _graph_path(repository_id, DATA_GRAPH),
            body=(FIXTURES / "nonconforming-data.ttl").read_bytes(),
            content_type="text/turtle",
        )

    error = rejected.value
    try:
        rejection_body = error.read().decode("utf-8", errors="replace")
    finally:
        error.close()

    assert (
        "shacl" in rejection_body.lower()
        or "ValidationReport" in rejection_body
    ), (
        "Expected a SHACL validation rejection, "
        f"but received HTTP {error.code}: {rejection_body}"
    )

    assert len(
        _read_graph(server_url, headers, repository_id, DATA_GRAPH)
    ) == 0, "Rejected data must not remain committed."

    # Conforming data must commit and retain its RDF meaning.
    conforming_bytes = (FIXTURES / "conforming-data.ttl").read_bytes()
    expected_data = Graph().parse(
        data=conforming_bytes.decode("utf-8"),
        format="turtle",
    )
    _request(
        server_url,
        headers,
        "POST",
        _graph_path(repository_id, DATA_GRAPH),
        body=conforming_bytes,
        content_type="text/turtle",
    )

    committed_data = _read_graph(
        server_url,
        headers,
        repository_id,
        DATA_GRAPH,
    )
    _assert_equivalent(
        committed_data,
        expected_data,
        "Committed conforming data",
    )   