"""GDB-1R1S2: Report an unreachable GraphDB server.

Simulates connection refusal at the HTTP transport boundary.
Does not contact GraphDB or create, modify, or delete repositories.
"""

from pathlib import Path
from urllib.error import URLError

import pytest

from owb_graphdb.client import GraphDBClient
from owb_graphdb.configuration import RepositoryConfiguration
from owb_graphdb.provisioning import provision_repository


FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def test_gdb_1_r1_s2_report_unreachable_graphdb_server(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    server_url = "http://127.0.0.1:7200"
    attempted_requests: list[tuple[str, str]] = []

    def refuse_connection(request, *args, **kwargs):
        attempted_requests.append(
            (request.get_method(), request.full_url)
        )
        raise URLError(ConnectionRefusedError("Connection refused"))

    monkeypatch.setattr(
        "owb_graphdb.client.urlopen",
        refuse_connection,
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
    assert "cannot connect" in result.message.lower()
    assert server_url in result.message

    assert attempted_requests == [
        ("GET", f"{server_url}/rest/repositories"),
    ], "Setup must stop after the failed connection attempt."