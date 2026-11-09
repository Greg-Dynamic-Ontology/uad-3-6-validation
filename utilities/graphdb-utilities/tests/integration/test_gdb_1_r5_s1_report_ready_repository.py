"""GDB-1R5S1: Report repository readiness with identity and verified metadata.

Requires GraphDB once the verification operation exists. Creates one uniquely
named disposable repository and deletes only that repository in teardown.
"""

import os
import json
from dataclasses import asdict, is_dataclass
from hashlib import sha256
from decimal import Decimal
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit
from uuid import uuid4

import pytest
from rdflib import Graph, Literal, Namespace, RDF, URIRef, XSD
from rdflib.compare import isomorphic

from owb_graphdb import validation
from owb_graphdb.client import GraphDBClient
from owb_graphdb.configuration import RepositoryConfiguration
from owb_graphdb.setup import setup_repository
from owb_graphdb.shapes import retrieve_shape_set

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
REP = Namespace("http://www.openrdf.org/config/repository#")
EX = Namespace("https://example.org/graphdb-utilities/test/")
PREFIX = "owb-gdb-1-r5-s1-"
DATA_GRAPH = "urn:owb:graphdb:test:existing-data"
VERIFICATION_GRAPH = "urn:owb:graphdb:test:verification"
PROTECTED_GRAPHS = (
    DATA_GRAPH,
    "urn:owb:graphdb:shapes",
    "http://rdf4j.org/schema/rdf4j#SHACLShapeGraph",
    "urn:owb:graphdb:shape-set-metadata",
)


def _parse(content):
    graph = Graph()
    if content.strip():
        graph.parse(data=content, format="turtle")
    return graph


def _normalized(graph):
    result = Graph()
    for subject, predicate, obj in graph:
        if isinstance(obj, Literal) and obj.datatype is None and obj.language is None:
            obj = Literal(str(obj), datatype=XSD.string)
        elif isinstance(obj, Literal) and obj.datatype == XSD.decimal:
            # Compare decimal values while retaining their exact datatype.
            # Do not use the production comparison helper as the test oracle.
            value = obj.toPython()
            if isinstance(value, Decimal) and value.is_finite():
                lexical = format(value, "f")
                if "." in lexical:
                    lexical = lexical.rstrip("0").rstrip(".")
                if value == 0:
                    lexical = "0"
                obj = Literal(lexical, datatype=XSD.decimal, normalize=False)
        result.add((subject, predicate, obj))
    return result


def _equivalent(left, right):
    return isomorphic(_normalized(left), _normalized(right))


def _path(repository_id, graph_iri):
    query = urlencode({"context": f"<{graph_iri}>", "infer": "false"})
    return f"/repositories/{repository_id}/statements?{query}"


def _read(client, repository_id, graph_iri):
    return _parse(client.request(
        method="GET", path=_path(repository_id, graph_iri), accept="text/turtle",
    ))


@pytest.mark.integration
def test_gdb_1_r5_s1_report_ready_repository(tmp_path):
    server_url = os.environ.get("GRAPHDB_TEST_SERVER_URL", "http://localhost:7200").rstrip("/")
    # A harmless synthetic header exercises exclusion of supplied header values
    # without introducing a fake Authorization header on a secured server.
    secret_marker = "test-only-secret-" + uuid4().hex
    headers = {"X-Verification-Test-Secret": secret_marker}
    authorization = os.environ.get("GRAPHDB_AUTHORIZATION")
    if authorization:
        headers["Authorization"] = authorization
    client = GraphDBClient(server_url=server_url, headers=headers, timeout_seconds=30)
    observer = GraphDBClient(server_url=server_url, headers=headers, timeout_seconds=30)
    repository_id = PREFIX + uuid4().hex

    config_graph = Graph().parse(FIXTURES / "repository-config.ttl", format="turtle")
    roots = list(config_graph.subjects(RDF.type, REP.Repository))
    assert len(roots) == 1
    config_graph.set((roots[0], REP.repositoryID, Literal(repository_id)))
    config_path = tmp_path / "repository-config.ttl"
    config_graph.serialize(destination=str(config_path), format="turtle")
    configuration = RepositoryConfiguration(
        server_url=server_url,
        repository_id=repository_id,
        repository_config_path=config_path,
        shapes_path=FIXTURES / "shapes.ttl",
        shapes_version="1.0.0",
        data_graph_iris=(DATA_GRAPH, VERIFICATION_GRAPH),
    )
    created = False
    try:
        initial = setup_repository(client=client, configuration=configuration)
        assert initial.success and initial.ready, initial.message
        created = True

        # Given setup and both verification checks have succeeded.
        conforming = Graph().parse(FIXTURES / "conforming-data.ttl", format="turtle")
        positive = validation.verify_conforming_dataset(
            client=client, configuration=configuration,
            dataset=conforming, verification_graph_iri=VERIFICATION_GRAPH,
        )
        # Existing successful conforming checks return None; an explicit result
        # must report success, never an unnoticed cleanup failure.
        if positive is not None:
            assert positive.success is True, positive.message
        assert not _read(observer, repository_id, VERIFICATION_GRAPH)

        nonconforming = Graph().parse(FIXTURES / "nonconforming-data.ttl", format="turtle")
        negative = validation.verify_nonconforming_dataset(
            client=client, configuration=configuration,
            dataset=nonconforming, verification_graph_iri=VERIFICATION_GRAPH,
        )
        assert negative.success is True, negative.message
        assert not _read(observer, repository_id, VERIFICATION_GRAPH)

        installed = retrieve_shape_set(client=observer, configuration=configuration)
        expected_digest = sha256(configuration.shapes_path.read_bytes()).hexdigest()
        assert installed.version == configuration.shapes_version
        assert installed.content_digest == expected_digest
        assert installed.data_graph_iris == configuration.data_graph_iris

        # When the utility returns its result for this verified repository.
        # This scenario covers the success-result contract; it does not claim
        # that setup alone performs the verification operations invoked above.
        result = setup_repository(client=client, configuration=configuration)
        assert result is not None
        assert result.success is True, result.message
        assert result.ready is True, result.message

        # Check secret exclusion without including the result or secret in an
        # assertion error if the result accidentally contains sensitive data.
        fields = asdict(result) if is_dataclass(result) else vars(result)
        serialized = json.dumps(fields, default=str, sort_keys=True) + repr(result)
        secrets = [secret_marker]
        if authorization:
            secrets.append(authorization)
            if " " in authorization:
                secrets.append(authorization.split(" ", 1)[1])
        assert not any(secret and secret in serialized for secret in secrets), (
            "The ready result must not contain authentication secrets or supplied header values."
        )
        assert not ({"headers", "authorization", "credentials", "password", "token"}
                    & {str(key).lower() for key in fields}), (
            "The ready result must not expose credential or authentication fields."
        )

        required_fields = (
            "server_url", "repository_id", "shapes_version",
            "content_digest", "data_graph_iris",
        )
        for name in required_fields:
            assert hasattr(result, name), (
                f"GDB-1R5S1 requires the ready result to identify {name}."
            )
        assert result.server_url == server_url
        assert result.repository_id == repository_id
        assert result.shapes_version == installed.version
        assert result.content_digest == installed.content_digest
        assert tuple(result.data_graph_iris) == installed.data_graph_iris
        assert not _read(observer, repository_id, VERIFICATION_GRAPH), (
            "Returning a ready result must not leave verification RDF behind."
        )
    finally:
        if created:
            assert repository_id.startswith(PREFIX)
            assert len(repository_id.removeprefix(PREFIX)) == 32
            client.request(method="DELETE", path=f"/rest/repositories/{repository_id}")
