"""IT-64R7S1: report repository unavailability without local fallback."""

import builtins
import io
from urllib.error import URLError

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, XSD

import app.adapters.customer_rdf_store as store_module


def test_it_64_r7_s1_report_unavailable_repository(monkeypatch, tmp_path):
    # No server is contacted. The transport fails before any request can be
    # accepted, distinguishing unavailability from an uncertain commit outcome.
    repository_url = "http://127.0.0.1:7200/repositories/uad-customer-test-it64-unavailable"
    graph_iri = "urn:uad:test:it64:r7:s1:customer"
    customer = Namespace("urn:uad:customer:")
    account = URIRef("urn:uad:test:account:it64-r7-s1")
    dataset = Graph()
    dataset.add((account, RDF.type, customer.CustomerAccount))
    dataset.add((account, customer.name, Literal("Unavailable repository test", datatype=XSD.string)))
    dataset.add((account, customer.createdAt, Literal(
        "2026-11-05T12:00:00Z", datatype=XSD.dateTime,
    )))

    # An existing local Turtle fixture must not become a substitute store.
    local_fixture = tmp_path / "customer-data.ttl"
    original_bytes = b"@prefix test: <urn:uad:test:> .\ntest:sentinel test:state test:unchanged .\n"
    local_fixture.write_bytes(original_bytes)
    monkeypatch.chdir(tmp_path)
    requests = []
    file_write_attempts = []
    refused = URLError(ConnectionRefusedError("Simulated repository connection refusal"))
    real_open = builtins.open
    real_io_open = io.open

    def unavailable(request, *args, **kwargs):
        requests.append(request)
        raise refused

    def guard_open(delegate):
        def guarded(file, mode="r", *args, **kwargs):
            if any(flag in str(mode) for flag in ("w", "a", "x", "+")):
                file_write_attempts.append(str(file))
                raise AssertionError("Customer persistence must not write a local fallback file.")
            return delegate(file, mode, *args, **kwargs)
        return guarded

    failure = None
    returned_normally = False
    # Limit instrumentation to the adapter call so pytest can write its output.
    with monkeypatch.context() as patch:
        patch.setattr(store_module, "urlopen", unavailable)
        patch.setattr(builtins, "open", guard_open(real_open))
        patch.setattr(io, "open", guard_open(real_io_open))
        try:
            store_module.CustomerRdfStore(repository_url, graph_iri).commit(
                dataset, actor_id="urn:uad:test:system:it64-r7-s1",
            )
            returned_normally = True
        except Exception as error:
            failure = error

    assert requests, "The test must reach the simulated unavailable GraphDB transport."
    assert not returned_normally, "An unavailable repository must not be reported as a successful commit."
    assert failure is not None
    assert not file_write_attempts, "UAD attempted to write a local operational fallback."
    assert local_fixture.read_bytes() == original_bytes
    assert set(tmp_path.iterdir()) == {local_fixture}, "No local fallback artifacts may be created."

    # Proposed application failure contract: distinguish unavailable persistence
    # from validation rejection, stale versions, and unconfirmed commit outcomes.
    assert getattr(failure, "code", None) == "persistence_unavailable", (
        "IT-64R7S1 requires an identifiable persistence_unavailable failure, "
        f"but received {type(failure).__name__}."
    )
    assert getattr(failure, "committed", None) is False, (
        "A connection refused before any accepted request must not claim a commit."
    )
    assert getattr(failure, "repository_url", None) == repository_url
    assert "unavailable" in str(failure).lower(), (
        "The diagnostic must explain that persistence is unavailable."
    )
