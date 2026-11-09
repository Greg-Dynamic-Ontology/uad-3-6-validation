"""IT-64R2S2: reject a change that leaves customer RDF nonconforming."""

import json
import os
from urllib.error import HTTPError
from pathlib import Path
from uuid import uuid4

import pytest

from owb_graphdb.client import GraphDBClient
from owb_graphdb.configuration import RepositoryConfiguration
from owb_graphdb.setup import setup_repository

from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.compare import isomorphic
from rdflib.namespace import RDF, XSD

from app.adapters.customer_rdf_store import CustomerRdfStore




PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEST_SHAPES = """
@prefix customer: <urn:uad:customer:> .
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix test: <urn:uad:test:it64:shapes:> .

test:Account a sh:NodeShape ;
    sh:targetClass customer:CustomerAccount ;
    sh:property [ sh:path customer:name ; sh:minCount 1 ;
                  sh:maxCount 1 ; sh:datatype xsd:string ] ;
    sh:property [ sh:path customer:createdAt ; sh:minCount 1 ;
                  sh:maxCount 1 ; sh:datatype xsd:dateTime ] .

test:Membership a sh:NodeShape ;
    sh:targetClass customer:Membership ;
    sh:property [ sh:path customer:account ; sh:minCount 1 ;
                  sh:maxCount 1 ; sh:nodeKind sh:IRI ] ;
    sh:property [ sh:path customer:user ; sh:minCount 1 ;
                  sh:maxCount 1 ; sh:nodeKind sh:IRI ] ;
    sh:property [ sh:path customer:role ; sh:minCount 1 ;
                  sh:maxCount 1 ; sh:nodeKind sh:IRI ] .
"""


@pytest.fixture
def customer_test_repository_url(tmp_path):
    """Own the default repository lifecycle; never delete an explicit override."""
    configured = os.environ.get("UAD_CUSTOMER_RDF_TEST_REPOSITORY_URL", "").strip()
    if configured:
        # Existing opt-in behavior: the operator supplies a dedicated test
        # repository already provisioned with the intended customer shapes.
        yield configured
        return

    server_url = os.environ.get("GRAPHDB_TEST_SERVER_URL", "http://localhost:7200").rstrip("/")
    prefix = "uad-customer-test-it64-"
    repository_id = prefix + uuid4().hex
    client = GraphDBClient(server_url=server_url, timeout_seconds=30)
    template = (
        PROJECT_ROOT / "utilities/graphdb-utilities/tests/fixtures/repository-config.ttl"
    )
    config_graph = Graph().parse(template, format="turtle")
    rep = Namespace("http://www.openrdf.org/config/repository#")
    roots = list(config_graph.subjects(RDF.type, rep.Repository))
    assert len(roots) == 1
    config_graph.set((roots[0], rep.repositoryID, Literal(repository_id)))
    config_path = tmp_path / "repository-config.ttl"
    config_graph.serialize(destination=str(config_path), format="turtle")
    shapes_path = tmp_path / "customer-test-shapes.ttl"
    shapes_path.write_text(TEST_SHAPES, encoding="utf-8")
    result = setup_repository(
        client=client,
        configuration=RepositoryConfiguration(
            server_url=server_url,
            repository_id=repository_id,
            repository_config_path=config_path,
            shapes_path=shapes_path,
            shapes_version="it64-r2-s2-test-v1",
            data_graph_iris=("urn:uad:test:it64:r2:s2:customer",),
        ),
    )
    assert result.success and result.ready, result.message
    try:
        yield f"{server_url}/repositories/{repository_id}"
    finally:
        # Delete exactly the repository created by this fixture, never enumerate
        # or clean other repositories. This also removes its test provenance.
        assert repository_id.startswith(prefix)
        assert len(repository_id.removeprefix(prefix)) == 32
        client.request(method="DELETE", path=f"/rest/repositories/{repository_id}")


def _normalized_strings(graph: Graph) -> Graph:
    """Represent RDF 1.1 plain strings explicitly as xsd:string.

    Preserve language tags, all other datatypes, IRIs, and blank nodes.
    Neither the supplied graph nor the retrieved graph is modified.
    """
    normalized = Graph()
    for subject, predicate, obj in graph:
        if isinstance(obj, Literal) and obj.datatype is None and obj.language is None:
            obj = Literal(str(obj), datatype=XSD.string)
        normalized.add((subject, predicate, obj))
    return normalized

def _reports_missing_name(body: bytes, account_id: URIRef, name_path: URIRef) -> bool:
    """Recognize the actual constraint failure, including JSON-wrapped Turtle."""
    text = body.decode("utf-8", errors="replace")
    candidates = [text]

    def collect_strings(value):
        if isinstance(value, str):
            candidates.append(value)
        elif isinstance(value, dict):
            for item in value.values():
                collect_strings(item)
        elif isinstance(value, list):
            for item in value:
                collect_strings(item)

    try:
        collect_strings(json.loads(text))
    except (ValueError, RecursionError):
        pass

    sh = Namespace("http://www.w3.org/ns/shacl#")
    for candidate in candidates:
        variants = [candidate]
        for marker in ("@prefix", "PREFIX "):
            position = candidate.find(marker)
            if position > 0:
                variants.append(candidate[position:])
        for variant in variants:
            report_graph = Graph()
            try:
                report_graph.parse(data=variant, format="turtle")
            except Exception:
                continue
            for report in report_graph.subjects(RDF.type, sh.ValidationReport):
                if (report, sh.conforms, Literal(False)) not in report_graph:
                    continue
                for result in report_graph.objects(report, sh.result):
                    if (
                        (result, sh.focusNode, account_id) in report_graph
                        and (result, sh.resultPath, name_path) in report_graph
                        and (result, sh.sourceConstraintComponent,
                             sh.MinCountConstraintComponent) in report_graph
                    ):
                        return True
    return False


def test_it_64_r2_s2_reject_nonconforming_customer_change(customer_test_repository_url):
    repository_url = customer_test_repository_url
    graph_iri = "urn:uad:test:it64:r2:s2:customer"
    customer = Namespace("urn:uad:customer:")
    account_id = URIRef("urn:uad:test:account:it64-r2-s2")
    user_id = URIRef("urn:uad:test:user:it64-r2-s2")
    membership = BNode()
    original_name = Literal("Original customer name", datatype=XSD.string)

    initial = Graph()
    initial.add((account_id, RDF.type, customer.CustomerAccount))
    initial.add((account_id, customer.name, original_name))
    initial.add((account_id, customer.createdAt, Literal(
        "2026-11-05T12:00:00Z", datatype=XSD.dateTime,
    )))
    initial.add((user_id, RDF.type, customer.User))
    initial.add((membership, RDF.type, customer.Membership))
    initial.add((membership, customer.account, account_id))
    initial.add((membership, customer.user, user_id))
    initial.add((membership, customer.role, customer.Owner))

    writer = CustomerRdfStore(repository_url, graph_iri)
    writer.commit(initial, actor_id="urn:uad:test:system:it64-r2-s2")
    stored = CustomerRdfStore(repository_url, graph_iri).retrieve()
    assert isomorphic(_normalized_strings(initial), _normalized_strings(stored)), (
        "Prerequisite failed: the initial conforming dataset was not persisted."
    )

    # Keep the target class and other required values. Removing only the name
    # violates the installed Account shape's sh:minCount 1 constraint.
    proposed = Graph()
    for triple in stored:
        proposed.add(triple)
    proposed.remove((account_id, customer.name, None))

    rejection_body = None
    try:
        writer.commit(proposed, actor_id="urn:uad:test:system:it64-r2-s2")
    except HTTPError as error:
        try:
            rejection_body = error.read()
        finally:
            error.close()

    # Observe stored data before any fixture teardown could hide a bad commit.
    actual = CustomerRdfStore(repository_url, graph_iri).retrieve()
    assert rejection_body is not None, (
        "IT-64R2S2 requires rejection of a customer change that removes a "
        "required name, but the GraphDB transaction returned successfully."
    )
    assert _reports_missing_name(rejection_body, account_id, customer.name), (
        "The rejection must include a nonconforming SHACL report identifying "
        "this account's missing customer:name (MinCountConstraintComponent). "
        "An unrelated HTTP failure does not demonstrate SHACL enforcement."
    )
    assert isomorphic(_normalized_strings(stored), _normalized_strings(actual)), (
        "Rejecting the nonconforming change must leave the previously "
        "committed customer RDF unchanged."
    )
