"""GDB-1R4S1: Persist, retrieve, and remove conforming verification RDF.

Requires GraphDB once the verification operation exists. Creates one uniquely
named disposable repository and deletes only that repository in teardown.
"""

import os
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

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
REP = Namespace("http://www.openrdf.org/config/repository#")
EX = Namespace("https://example.org/graphdb-utilities/test/")
PREFIX = "owb-gdb-1-r4-s1-"
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
def test_gdb_1_r4_s1_verify_conforming_dataset(tmp_path):
    # Explicit capability assertion instead of a broken import or TypeError.
    verify = getattr(validation, "verify_conforming_dataset", None)
    assert callable(verify), (
        "GDB-1R4S1 requires verify_conforming_dataset(client=..., "
        "configuration=..., dataset=..., verification_graph_iri=...) "
        "to commit, read back, and clean up caller-supplied verification RDF."
    )

    server_url = os.environ.get("GRAPHDB_TEST_SERVER_URL", "http://localhost:7200")
    headers = {}
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

    # Distinct resource IRIs plus a relationship and several literal datatypes.
    dataset = Graph()
    for name in ("verification-a", "verification-b"):
        subject = EX[name]
        dataset.add((subject, RDF.type, EX.TestRecord))
        dataset.add((subject, EX.identifier, Literal(name, datatype=XSD.string)))
        dataset.add((subject, EX.label, Literal(name, datatype=XSD.string)))
    dataset.add((EX["verification-a"], EX.relatedTo, EX["verification-b"]))
    dataset.add((EX["verification-a"], EX.quantity, Literal(7, datatype=XSD.integer)))
    dataset.add((EX["verification-a"], EX.amount, Literal("12.50", datatype=XSD.decimal)))
    dataset.add((EX["verification-a"], EX.active, Literal(True, datatype=XSD.boolean)))
    expected = Graph()
    for triple in dataset:
        expected.add(triple)

    created = False
    try:
        setup_result = setup_repository(client=client, configuration=configuration)
        assert setup_result.success and setup_result.ready, setup_result.message
        created = True
        client.request(
            method="POST", path=_path(repository_id, DATA_GRAPH),
            body=(FIXTURES / "conforming-data.ttl").read_bytes(),
            content_type="text/turtle",
        )
        before = {iri: _read(observer, repository_id, iri) for iri in PROTECTED_GRAPHS}
        assert len(before[DATA_GRAPH]) > 0
        assert len(_read(observer, repository_id, VERIFICATION_GRAPH)) == 0
        durable_snapshots = []
        utility_reads = []
        requests = []

        class ObservedClient(GraphDBClient):
            def request(self, *, method, path, **kwargs):
                requests.append((method.upper(), path))
                response = super().request(method=method, path=path, **kwargs)
                parsed = urlsplit(path)
                contexts = parse_qs(parsed.query).get("context", [])
                if (
                    method.upper() == "GET"
                    and parsed.path == f"/repositories/{repository_id}/statements"
                    and f"<{VERIFICATION_GRAPH}>" in contexts
                ):
                    utility_reads.append(_parse(response))
                if method.upper() in {"POST", "PUT", "DELETE", "PATCH"}:
                    # A separate HTTP client observes committed server state,
                    # not the supplied Graph or an uncommitted transaction.
                    durable_snapshots.append(_read(observer, repository_id, VERIFICATION_GRAPH))
                return response

        verification_client = ObservedClient(
            server_url=server_url, headers=headers, timeout_seconds=30,
        )
        # Contract: normal return means verification succeeded; failures raise
        # a GraphDB utility exception, matching validation.py's convention.
        verify(
            client=verification_client,
            configuration=configuration,
            dataset=dataset,
            verification_graph_iri=VERIFICATION_GRAPH,
        )

        assert any(_equivalent(expected, graph) for graph in durable_snapshots), (
            "Verification RDF must become visible to an independent client after commit."
        )
        assert any(_equivalent(expected, graph) for graph in utility_reads), (
            "The utility must read back equivalent RDF, preserving IRIs, relationships, and datatypes."
        )
        assert len(_read(observer, repository_id, VERIFICATION_GRAPH)) == 0, (
            "The utility must remove its verification RDF before returning."
        )
        for iri, original in before.items():
            assert _equivalent(original, _read(observer, repository_id, iri)), (
                f"Verification changed pre-existing RDF in {iri}."
            )
        repository_endpoints = {
            "/rest/repositories", f"/rest/repositories/{repository_id}",
            f"/repositories/{repository_id}",
        }
        assert not [
            (method, path) for method, path in requests
            if method in {"DELETE", "POST", "PUT", "PATCH"}
            and urlsplit(path).path.rstrip("/") in repository_endpoints
        ], "Verification must preserve the repository rather than replace it."
    finally:
        # Test teardown happens AFTER the utility-cleanup assertion. It cannot
        # make missing utility cleanup pass. Never enumerate/delete other repos.
        if created:
            assert repository_id.startswith(PREFIX)
            assert len(repository_id.removeprefix(PREFIX)) == 32
            client.request(method="DELETE", path=f"/rest/repositories/{repository_id}")

