"""GDB-1R3S2: Identify incompatible settings without changing a repository."""

from io import BytesIO
from pathlib import Path

import pytest
from rdflib import Graph, Literal, Namespace
from rdflib.compare import isomorphic

from owb_graphdb.client import GraphDBClient
from owb_graphdb.configuration import RepositoryConfiguration
from owb_graphdb.setup import setup_repository


FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
SERVER_URL = "http://127.0.0.1:7200"
REPOSITORY_ID = "owb-graphdb-test"
GRAPHDB = Namespace("http://www.ontotext.com/config/graphdb#")


def test_gdb_1_r3_s2_detect_incompatible_repository_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configuration = RepositoryConfiguration(
        server_url=SERVER_URL,
        repository_id=REPOSITORY_ID,
        repository_config_path=FIXTURES / "repository-config.ttl",
        shapes_path=FIXTURES / "shapes.ttl",
        shapes_version="gdb-1-r3-s2",
        data_graph_iris=("urn:owb:graphdb:test:data",),
    )

    # Given an existing repository with SHACL enabled but a wrong ruleset.
    actual = Graph().parse(
        configuration.repository_config_path,
        format="turtle",
    )
    subjects = list(actual.subjects(GRAPHDB.ruleset, Literal("empty")))
    assert len(subjects) == 1, "Fixture must require the empty ruleset."
    actual.set((subjects[0], GRAPHDB.ruleset, Literal("rdfsplus-optimized")))

    configuration_bytes = actual.serialize(format="turtle").encode("utf-8")
    data_bytes = (FIXTURES / "conforming-data.ttl").read_bytes()
    data_before = Graph().parse(data=data_bytes, format="turtle")
    assert len(data_before) > 0, "Preservation requires existing RDF data."

    requests: list[tuple[str, str]] = []
    repositories_url = f"{SERVER_URL}/rest/repositories"
    repository_url = f"{repositories_url}/{REPOSITORY_ID}"
    statements_url = f"{SERVER_URL}/repositories/{REPOSITORY_ID}/statements"

    def fake_urlopen(request, timeout=None):
        method = request.get_method()
        url = request.full_url
        requests.append((method, url))

        # Reject every mutation, including delete/recreate or RDF updates.
        assert method == "GET", (
            f"Incompatible setup must not mutate the repository: {method} {url}"
        )

        if url == repositories_url:
            return BytesIO(
                b'[{"id": "owb-graphdb-test"}]'
            )
        if url == repository_url:
            return BytesIO(configuration_bytes)
        if url.split("?", 1)[0] == statements_url:
            return BytesIO(data_bytes)

        raise AssertionError(f"Unexpected GraphDB request: {method} {url}")

    monkeypatch.setattr("owb_graphdb.client.urlopen", fake_urlopen)
    client = GraphDBClient(server_url=SERVER_URL, timeout_seconds=1)

    # When the operator runs setup.
    result = setup_repository(client=client, configuration=configuration)

    # Then setup inspected the configuration and returned failure.
    assert ("GET", repository_url) in requests
    assert result is not None, "Setup must return a failure result."
    assert result.success is False
    assert result.ready is False

    # No write request may be attempted, even if setup catches its error.
    assert all(method == "GET" for method, _ in requests), requests

    configuration_after = Graph().parse(
        data=client.request(
            method="GET",
            path=f"/rest/repositories/{REPOSITORY_ID}",
            accept="text/turtle",
        ),
        format="turtle",
    )
    data_after = Graph().parse(
        data=client.request(
            method="GET",
            path=f"/repositories/{REPOSITORY_ID}/statements",
            accept="text/turtle",
        ),
        format="turtle",
    )
    assert isomorphic(actual, configuration_after)
    assert isomorphic(data_before, data_after)

    assert REPOSITORY_ID in result.message
    assert "ruleset" in result.message.lower(), (
        "Setup must identify the incompatible ruleset setting, "
        f"not merely report a generic mismatch: {result.message}"
    )