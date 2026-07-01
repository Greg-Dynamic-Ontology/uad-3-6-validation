"""Tests for loading and validating UAD 3.6 ontology Turtle files."""

from pathlib import Path

import pytest
from rdflib import Graph, URIRef
from rdflib.namespace import OWL, RDF

from app.core.namespaces import ONTOLOGY_DOCUMENT_IRI, UAD
from app.core.iri_minting import is_valid_local_name


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ONTOLOGY_DIR = PROJECT_ROOT / "ontologies"
CORE_ONTOLOGY_FILE = ONTOLOGY_DIR / "uad36-core.ttl"


def load_graph(path: Path) -> Graph:
    graph = Graph()
    graph.parse(path, format="turtle")
    return graph


def test_core_ontology_file_exists() -> None:
    assert CORE_ONTOLOGY_FILE.exists(), f"Missing ontology file: {CORE_ONTOLOGY_FILE}"


def test_core_ontology_file_parses_as_turtle() -> None:
    graph = load_graph(CORE_ONTOLOGY_FILE)

    assert len(graph) > 0


def test_core_ontology_declares_expected_ontology_iri() -> None:
    graph = load_graph(CORE_ONTOLOGY_FILE)

    assert (URIRef(ONTOLOGY_DOCUMENT_IRI), RDF.type, OWL.Ontology) in graph


def test_core_ontology_has_exactly_one_ontology_declaration() -> None:
    graph = load_graph(CORE_ONTOLOGY_FILE)

    ontology_subjects = set(graph.subjects(RDF.type, OWL.Ontology))

    assert ontology_subjects == {URIRef(ONTOLOGY_DOCUMENT_IRI)}


@pytest.mark.parametrize(
    "prefix",
    ["rdf", "rdfs", "owl", "xsd", "skos", "dcterms", "uad"],
)
def test_core_ontology_binds_required_prefixes(prefix: str) -> None:
    graph = load_graph(CORE_ONTOLOGY_FILE)
    namespaces = dict(graph.namespaces())

    assert prefix in namespaces


def test_uad_prefix_matches_namespace_constant() -> None:
    graph = load_graph(CORE_ONTOLOGY_FILE)
    namespaces = dict(graph.namespaces())

    assert str(namespaces["uad"]) == str(UAD)


def test_owl_classes_use_uad_namespace() -> None:
    graph = load_graph(CORE_ONTOLOGY_FILE)

    class_subjects = set(graph.subjects(RDF.type, OWL.Class))

    assert class_subjects, "Expected at least one owl:Class in the core ontology"
    for subject in class_subjects:
        assert isinstance(subject, URIRef)
        assert str(subject).startswith(str(UAD))


def test_owl_class_local_names_follow_iri_minting_policy() -> None:
    graph = load_graph(CORE_ONTOLOGY_FILE)

    for subject in graph.subjects(RDF.type, OWL.Class):
        local_name = str(subject).removeprefix(str(UAD))
        assert is_valid_local_name(local_name), f"Invalid UAD class local name: {local_name}"
