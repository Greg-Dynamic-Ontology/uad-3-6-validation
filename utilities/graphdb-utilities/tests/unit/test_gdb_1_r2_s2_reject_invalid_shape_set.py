"""GDB-1R2S2: Reject an invalid shape set during repository setup."""

from io import BytesIO
from pathlib import Path

import pytest

from owb_graphdb.client import GraphDBClient
from owb_graphdb.configuration import RepositoryConfiguration
from owb_graphdb.provisioning import provision_repository


FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def test_gdb_1_r2_s2_reject_invalid_shape_set(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    server_url = "http://127.0.0.1:7200"
    repository_id = "owb-graphdb-test"
    repositories_url = f"{server_url}/rest/repositories"
    configuration_url = f"{repositories_url}/{repository_id}"

    repository_config_path = FIXTURES / "repository-config.ttl"
    repository_config = repository_config_path.read_bytes()

    invalid_shapes_path = tmp_path / "invalid-shapes.ttl"
    invalid_shapes_path.write_text(
        """
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix ex: <urn:owb:graphdb:test:> .

ex:ExampleShape a sh:NodeShape ;
    sh:targetClass ex:Example ;
    sh:property [
        sh:path ex:name ;
        sh:minCount
""",
        encoding="utf-8",
    )

    attempted_requests: list[tuple[str, str]] = []

    def simulated_graphdb(request, *args, **kwargs):
        method = request.get_method()
        url = request.full_url
        attempted_requests.append((method, url))

        if method == "GET" and url == repositories_url:
            return BytesIO(b"[]")

        if method == "POST" and url == repositories_url:
            return BytesIO(b"")

        if method == "GET" and url == configuration_url:
            return BytesIO(repository_config)

        raise AssertionError(
            "Invalid shapes must be rejected before any shape-set upload. "
            f"Unexpected request: {method} {url}"
        )

    monkeypatch.setattr(
        "owb_graphdb.client.urlopen",
        simulated_graphdb,
    )

    configuration = RepositoryConfiguration(
        server_url=server_url,
        repository_id=repository_id,
        repository_config_path=repository_config_path,
        shapes_path=invalid_shapes_path,
        shapes_version="invalid-test-v1",
        data_graph_iris=("urn:owb:graphdb:test:data",),
    )
    client = GraphDBClient(
        server_url=server_url,
        timeout_seconds=1.0,
    )

    result = provision_repository(
        client=client,
        configuration=configuration,
    )

    assert result is not None, (
        "Setup must return a failure result for an invalid shape set."
    )
    assert result.success is False
    assert result.ready is False

    message = result.message.lower()
    assert "shape" in message
    assert any(
        term in message
        for term in ("invalid", "parse", "syntax")
    ), "Setup must explain the shape-set error."

    data_endpoint = f"{server_url}/repositories/{repository_id}"
    data_writes = [
        (method, url)
        for method, url in attempted_requests
        if method in {"POST", "PUT", "PATCH", "DELETE"}
        and (
            url == data_endpoint
            or url.startswith(f"{data_endpoint}/")
        )
    ]
    assert data_writes == [], (
        "An unparseable shape set must not cause a partial "
        "shape-set installation to be committed to GraphDB."
    )