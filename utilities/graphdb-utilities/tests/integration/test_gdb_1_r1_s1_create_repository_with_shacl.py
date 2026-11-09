"""GDB-1R1S1: Create a repository with SHACL validation.

Requires a running GraphDB server and permission to create and delete
repositories.

Before each run, delete repositories beginning with "owb-gdb-1".
Read configuration only from the repository created by this test.
Do not export or compare the contents of other repositories.

Leave the newly created repository available for inspection.
Run this test serially.
"""

import json
import os
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen
from uuid import uuid4

import pytest
from rdflib import BNode, Graph, Literal, Namespace, RDF, XSD

from owb_graphdb.client import GraphDBClient
from owb_graphdb.configuration import RepositoryConfiguration
from owb_graphdb.provisioning import provision_repository


FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
TEST_REPOSITORY_PREFIX = "owb-gdb-1"

REP = Namespace("http://www.openrdf.org/config/repository#")
SAIL = Namespace("http://www.openrdf.org/config/sail#")
SHACL_CONFIG = Namespace("http://rdf4j.org/config/sail/shacl#")


def _get(
    server_url: str,
    path: str,
    headers: dict[str, str],
    accept: str,
) -> bytes:
    """Read GraphDB independently of the utility under test."""
    request = Request(
        f"{server_url}{path}",
        headers={**headers, "Accept": accept},
        method="GET",
    )
    with urlopen(request, timeout=30) as response:
        return response.read()


def _repository_ids(
    server_url: str,
    headers: dict[str, str],
) -> set[str]:
    """List identifiers without retrieving repository contents."""
    payload = _get(
        server_url,
        "/rest/repositories",
        headers,
        "application/json",
    )
    return {item["id"] for item in json.loads(payload)}


def _delete_previous_test_repositories(
    server_url: str,
    headers: dict[str, str],
) -> set[str]:
    """Delete only repositories in the authorized test namespace."""
    original_ids = _repository_ids(server_url, headers)
    test_ids = {
        repository_id
        for repository_id in original_ids
        if repository_id.startswith(TEST_REPOSITORY_PREFIX)
    }

    for repository_id in sorted(test_ids):
        encoded_id = quote(repository_id, safe="")
        request = Request(
            f"{server_url}/rest/repositories/{encoded_id}",
            headers=headers,
            method="DELETE",
        )
        with urlopen(request, timeout=30) as response:
            response.read()

    remaining_ids = _repository_ids(server_url, headers)
    expected_ids = original_ids - test_ids

    assert remaining_ids == expected_ids, (
        "Test cleanup did not leave the expected repositories. "
        f"Expected: {sorted(expected_ids)!r}; "
        f"found: {sorted(remaining_ids)!r}."
    )

    return remaining_ids


def _configuration(
    server_url: str,
    repository_id: str,
    headers: dict[str, str],
) -> Graph:
    """Retrieve the configuration of the test's own repository."""
    payload = _get(
        server_url,
        f"/rest/repositories/{quote(repository_id, safe='')}",
        headers,
        "text/turtle",
    )
    return Graph().parse(data=payload, format="turtle")


def _configuration_boolean(value) -> bool | None:
    """Interpret Boolean representations in exported settings."""
    if not isinstance(value, Literal) or value.language is not None:
        return None

    if value.datatype not in (None, XSD.string, XSD.boolean):
        return None

    return {
        "true": True,
        "1": True,
        "false": False,
        "0": False,
    }.get(str(value).strip())


def _normalized_configuration(source: Graph) -> Graph:
    """Normalize validationEnabled only within repository configuration."""
    result = Graph()

    for subject, predicate, obj in source:
        if predicate == SHACL_CONFIG.validationEnabled:
            value = _configuration_boolean(obj)
            if value is not None:
                obj = Literal(value)

        result.add((subject, predicate, obj))

    return result


def _assert_required_configuration(
    expected: Graph,
    actual: Graph,
) -> None:
    """Require supplied settings while allowing additional GraphDB defaults."""
    expected = _normalized_configuration(expected)
    actual = _normalized_configuration(actual)
    variables: dict[BNode, str] = {}

    def term(value) -> str:
        if isinstance(value, BNode):
            if value not in variables:
                variables[value] = f"?node{len(variables)}"
            return variables[value]

        return value.n3()

    patterns = "\n".join(
        f"{term(subject)} {term(predicate)} {term(obj)} ."
        for subject, predicate, obj in expected
    )

    result = actual.query(f"ASK WHERE {{\n{patterns}\n}}")

    assert bool(result.askAnswer), (
        "The created repository does not match the supplied configuration."
    )


@pytest.mark.integration
def test_gdb_1_r1_s1_create_repository_with_shacl(
    tmp_path: Path,
) -> None:
    server_url = os.environ.get(
        "GRAPHDB_TEST_SERVER_URL",
        "http://localhost:7200",
    ).rstrip("/")

    authorization = os.environ.get("GRAPHDB_AUTHORIZATION")
    headers = {"Authorization": authorization} if authorization else {}

    # Cleanup is restricted to the explicitly authorized test prefix.
    existing_ids = _delete_previous_test_repositories(
        server_url,
        headers,
    )

    repository_id = f"{TEST_REPOSITORY_PREFIX}-r1-s1-{uuid4().hex}"
    config_path = tmp_path / "repository-config.ttl"

    required = Graph().parse(
        FIXTURES / "repository-config.ttl",
        format="turtle",
    )

    repositories = list(required.subjects(RDF.type, REP.Repository))
    assert len(repositories) == 1, (
        "The configuration fixture must define exactly one repository."
    )

    required.set(
        (repositories[0], REP.repositoryID, Literal(repository_id))
    )
    required.serialize(destination=config_path, format="turtle")

    assert repository_id not in existing_ids

    configuration = RepositoryConfiguration(
        server_url=server_url,
        repository_id=repository_id,
        repository_config_path=config_path,
        shapes_path=FIXTURES / "shapes.ttl",
        shapes_version="1.0.0",
        data_graph_iris=(
            "https://example.org/graphdb-utilities/test/data",
        ),
    )

    client = GraphDBClient(
        server_url=server_url,
        headers=headers,
        timeout_seconds=30,
    )

    provision_repository(
        client=client,
        configuration=configuration,
    )

    # Check identifiers only. Never retrieve other repositories' data.
    after_ids = _repository_ids(server_url, headers)
    assert after_ids == existing_ids | {repository_id}, (
        "Provisioning must add exactly the requested repository "
        "and preserve existing repository identifiers."
    )

    actual = _configuration(
        server_url,
        repository_id,
        headers,
    )

    shacl_sails = list(
        actual.subjects(SAIL.sailType, Literal("rdf4j:ShaclSail"))
    )
    assert shacl_sails, "The repository has no SHACL sail."

    for sail in shacl_sails:
        settings = list(
            actual.objects(sail, SHACL_CONFIG.validationEnabled)
        )

        assert settings, "The SHACL enablement setting is missing."
        assert all(
            _configuration_boolean(setting) is True
            for setting in settings
        ), "SHACL validation is disabled or has an unreadable setting."

    _assert_required_configuration(required, actual)