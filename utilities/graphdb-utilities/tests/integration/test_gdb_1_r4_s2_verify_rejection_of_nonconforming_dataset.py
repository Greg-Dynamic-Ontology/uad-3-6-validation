"""GDB-1R4S2: Verify SHACL rejection without committing invalid RDF.

Requires GraphDB once the verification operation exists. Creates one uniquely
named disposable repository and deletes only that repository in teardown.
"""

import os
from io import BytesIO
from urllib.error import HTTPError

import owb_graphdb.client as client_module
from owb_graphdb.shapes import retrieve_shape_set
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
PREFIX = "owb-gdb-1-r4-s2-"
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
def test_gdb_1_r4_s2_verify_rejection_of_nonconforming_dataset(tmp_path, monkeypatch):
    verify = getattr(validation, "verify_nonconforming_dataset", None)
    assert callable(verify), (
        "GDB-1R4S2 requires verify_nonconforming_dataset(client=..., "
        "configuration=..., dataset=..., verification_graph_iri=...) "
        "to report confirmed SHACL rejection as a successful verification outcome."
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

    # Use a different focus node from the pre-existing conforming record.
    # Include valid triples too: rejection must roll back the whole dataset.
    invalid = Graph().parse(FIXTURES / "nonconforming-data.ttl", format="turtle")
    dataset = Graph()
    focus = EX["verification-invalid"]
    for subject, predicate, obj in invalid:
        dataset.add((focus if subject == EX["record-001"] else subject, predicate, obj))
    valid = EX["verification-valid"]
    dataset.add((valid, RDF.type, EX.TestRecord))
    dataset.add((valid, EX.identifier, Literal("verification-valid", datatype=XSD.string)))
    dataset.add((valid, EX.label, Literal("Valid companion record", datatype=XSD.string)))
    assert (focus, RDF.type, EX.TestRecord) in dataset
    assert not list(dataset.objects(focus, EX.identifier))

    created = False
    try:
        setup_result = setup_repository(client=client, configuration=configuration)
        assert setup_result.success and setup_result.ready, setup_result.message
        created = True
        installed = retrieve_shape_set(client=observer, configuration=configuration)
        SH = Namespace("http://www.w3.org/ns/shacl#")
        assert (EX.TestRecordShape, SH.targetClass, EX.TestRecord) in installed.graph
        assert any(
            (prop, SH.path, EX.identifier) in installed.graph
            and any(int(count) >= 1 for count in installed.graph.objects(prop, SH.minCount))
            for prop in installed.graph.objects(EX.TestRecordShape, SH.property)
        ), "The identified active shape must require the missing identifier."
        assert VERIFICATION_GRAPH in installed.data_graph_iris

        client.request(
            method="POST", path=_path(repository_id, DATA_GRAPH),
            body=(FIXTURES / "conforming-data.ttl").read_bytes(),
            content_type="text/turtle",
        )
        before = {iri: _read(observer, repository_id, iri) for iri in PROTECTED_GRAPHS}
        assert len(before[DATA_GRAPH]) > 0
        assert not _read(observer, repository_id, VERIFICATION_GRAPH)
        rejection_responses = []
        attempted_writes = []
        snapshots = []
        real_urlopen = client_module.urlopen

        def recording_urlopen(request, *args, **kwargs):
            # Real HTTP, not a simulated SHACL rejection. Restore the error
            # stream so production code can consume the same server response.
            try:
                return real_urlopen(request, *args, **kwargs)
            except HTTPError as error:
                try:
                    body = error.read()
                    if request.get_method() in {"POST", "PUT"}:
                        rejection_responses.append((error.code, body))
                    # Rebuild the wrapper around the exact real server response.
                    # Assigning error.fp does not reset its cached read method.
                    replay = HTTPError(
                        error.url, error.code, error.msg,
                        error.headers, BytesIO(body),
                    )
                finally:
                    error.close()
                raise replay from None

        class ObservedClient(GraphDBClient):
            def request(self, *, method, path, **kwargs):
                mutating = method.upper() in {"POST", "PUT", "DELETE", "PATCH"}
                if mutating:
                    attempted_writes.append((method.upper(), path))
                try:
                    return super().request(method=method, path=path, **kwargs)
                finally:
                    if mutating:
                        # Observe immediately after rejection, BEFORE any later
                        # cleanup could hide an incorrectly committed dataset.
                        snapshots.append(_read(observer, repository_id, VERIFICATION_GRAPH))

        with monkeypatch.context() as transport:
            transport.setattr("owb_graphdb.client.urlopen", recording_urlopen)
            result = verify(
                client=ObservedClient(server_url=server_url, headers=headers, timeout_seconds=30),
                configuration=configuration,
                dataset=dataset,
                verification_graph_iri=VERIFICATION_GRAPH,
            )

        assert any(method in {"POST", "PUT"} for method, _ in attempted_writes), (
            "The utility must actually attempt the RDF write."
        )
        assert rejection_responses, "GraphDB must reject the attempted transaction."
        assert any(
            ("shacl" in body.decode("utf-8", errors="replace").lower()
             or "validationreport" in body.decode("utf-8", errors="replace").lower())
            for _, body in rejection_responses
        ), "An HTTP failure alone does not establish SHACL rejection."
        assert snapshots and all(len(graph) == 0 for graph in snapshots), (
            "No part of the attempted dataset may become committed, even temporarily."
        )
        assert not _read(observer, repository_id, VERIFICATION_GRAPH)
        for iri, original in before.items():
            assert _equivalent(original, _read(observer, repository_id, iri)), (
                f"Verification changed pre-existing RDF in {iri}."
            )

        # Successful VERIFICATION means the expected validation rejection was
        # observed; it does not mean the nonconforming RDF was accepted.
        assert result is not None, "Return an explicit verification outcome."
        assert result.success is True, result.message
        message = result.message.lower()
        assert "shacl" in message and "reject" in message and "expected" in message, (
            "Report SHACL rejection as the expected verification outcome: " + result.message
        )
    finally:
        if created:
            assert repository_id.startswith(PREFIX)
            assert len(repository_id.removeprefix(PREFIX)) == 32
            client.request(method="DELETE", path=f"/rest/repositories/{repository_id}")



