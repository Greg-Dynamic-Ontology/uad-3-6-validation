"""GDB-1R2S3: Report failure after repository creation."""

from io import BytesIO
from pathlib import Path
from urllib.error import HTTPError

import pytest

from owb_graphdb.client import GraphDBClient
from owb_graphdb.configuration import RepositoryConfiguration
from owb_graphdb.setup import setup_repository


FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
REPOSITORY_ID = "owb-graphdb-test"
SERVER_URL = "http://127.0.0.1:7200"


def test_gdb_1_r2_s3_report_failure_after_repository_creation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failed installation leaves the created repository not ready."""
    configuration = RepositoryConfiguration(
        server_url=SERVER_URL,
        repository_id=REPOSITORY_ID,
        repository_config_path=FIXTURES / "repository-config.ttl",
        shapes_path=FIXTURES / "shapes.ttl",
        shapes_version="gdb-1-r2-s3",
        data_graph_iris=("urn:owb:graphdb:test:data",),
    )
    configuration_bytes = configuration.repository_config_path.read_bytes()
    requests: list[tuple[str, str]] = []
    repository_created = False
    installation_attempted = False

    def fake_urlopen(request, timeout=None):
        nonlocal repository_created, installation_attempted

        method = request.get_method()
        url = request.full_url
        requests.append((method, url))

        repositories_url = f"{SERVER_URL}/rest/repositories"
        repository_url = f"{repositories_url}/{REPOSITORY_ID}"
        statements_url = (
            f"{SERVER_URL}/repositories/{REPOSITORY_ID}/statements"
        )

        if method == "GET" and url == repositories_url:
            return BytesIO(b"[]")

        if method == "POST" and url == repositories_url:
            repository_created = True
            return BytesIO(b"")

        if method == "GET" and url == repository_url:
            assert repository_created
            return BytesIO(configuration_bytes)

        if method == "GET" and url.startswith(statements_url):
            assert repository_created
            return BytesIO(b"")

        if method == "POST" and url == statements_url:
            assert repository_created
            installation_attempted = True
            raise HTTPError(
                url=url,
                code=500,
                msg="Simulated shape-set installation failure",
                hdrs=None,
                fp=BytesIO(b"Shape-set installation failed"),
            )

        raise AssertionError(f"Unexpected GraphDB request: {method} {url}")

    monkeypatch.setattr("owb_graphdb.client.urlopen", fake_urlopen)
    client = GraphDBClient(server_url=SERVER_URL, timeout_seconds=1)

    result = setup_repository(
        client=client,
        configuration=configuration,
    )

    assert repository_created, "Setup must first create the repository."
    assert not any(method == "DELETE" for method, _ in requests), (
        "Setup must preserve the repository after installation fails."
    )
    assert result is not None, (
        "Setup must return a failure result after shape-set "
        "installation fails."
    )
    assert installation_attempted, (
        "Setup must attempt to install the supplied shape set."
    )
    assert result.success is False
    assert result.ready is False

    message = result.message.lower()

    assert REPOSITORY_ID in result.message, (
        "The result must identify the created repository."
    )
    assert "created" in message, (
        "The result must explain that repository creation succeeded."
    )
    assert "shape" in message and "install" in message, (
        "The result must identify shape-set installation as the failed step."
    )
    assert "fail" in message, (
        "The result must explicitly report the setup failure."
    )