"""GDB-1R1S3: Report insufficient provisioning permissions."""

from io import BytesIO
from pathlib import Path
from urllib.error import HTTPError

import pytest

from owb_graphdb.client import GraphDBClient
from owb_graphdb.configuration import RepositoryConfiguration
from owb_graphdb.provisioning import provision_repository


FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def test_gdb_1_r1_s3_report_insufficient_provisioning_permissions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    server_url = "http://127.0.0.1:7200"
    repositories_url = f"{server_url}/rest/repositories"
    attempted_requests: list[tuple[str, str]] = []

    def deny_repository_creation(request, *args, **kwargs):
        method = request.get_method()
        url = request.full_url
        attempted_requests.append((method, url))

        if method == "GET" and url == repositories_url:
            # The server is reachable; the requested repository is absent.
            return BytesIO(b"[]")

        if method == "POST" and url == repositories_url:
            # The operator lacks permission to create repositories.
            raise HTTPError(
                url,
                403,
                "Forbidden",
                {},
                BytesIO(b"Permission denied"),
            )

        raise AssertionError(f"Unexpected request: {method} {url}")

    monkeypatch.setattr(
        "owb_graphdb.client.urlopen",
        deny_repository_creation,
    )

    configuration = RepositoryConfiguration(
        server_url=server_url,
        repository_id="owb-graphdb-test",
        repository_config_path=FIXTURES / "repository-config.ttl",
        shapes_path=FIXTURES / "shapes.ttl",
        shapes_version="test-v1",
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

    assert result is not None, "Setup must return a failure result."
    assert result.success is False
    assert result.ready is False
    assert "not authorized" in result.message.lower()

    assert attempted_requests == [
        ("GET", repositories_url),
        ("POST", repositories_url),
    ], "Setup must stop after repository creation is refused."