from pathlib import Path

import pytest
from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS, SKOS


PROJECT_ROOT = Path(__file__).resolve().parents[1]

CORE_ONTOLOGY_FILE = PROJECT_ROOT / "ontologies" / "uad36-core.ttl"
URAR_MEANING_FILE = PROJECT_ROOT / "ontologies" / "urar-meaning.ttl"
MODEL_DOC_FILE = PROJECT_ROOT / "docs" / "architecture" / "urar-meaning-model.md"

UAD = Namespace("https://dynamicontology.com/uad36/ontology#")

UAD_ONTOLOGY_IRI = URIRef("https://dynamicontology.com/uad36/ontology")
URAR_MEANING_ONTOLOGY_IRI = URIRef("https://dynamicontology.com/uad36/urar-meaning")


@pytest.fixture(scope="module")
def urar_graph() -> Graph:
    graph = Graph()
    graph.parse(URAR_MEANING_FILE, format="turtle")
    return graph


@pytest.fixture(scope="module")
def combined_graph() -> Graph:
    graph = Graph()
    graph.parse(CORE_ONTOLOGY_FILE, format="turtle")
    graph.parse(URAR_MEANING_FILE, format="turtle")
    return graph


def test_core_ontology_file_exists():
    assert CORE_ONTOLOGY_FILE.exists()


def test_urar_meaning_ontology_file_exists():
    assert URAR_MEANING_FILE.exists()


def test_urar_meaning_model_doc_exists():
    assert MODEL_DOC_FILE.exists()


def test_core_ontology_parses_as_turtle(combined_graph: Graph):
    assert len(combined_graph) > 0


def test_urar_meaning_parses_as_turtle(urar_graph: Graph):
    assert len(urar_graph) > 0


def test_urar_meaning_does_not_declare_own_ontology(urar_graph: Graph):
    ontology_declarations = set(urar_graph.subjects(RDF.type, OWL.Ontology))

    assert URAR_MEANING_ONTOLOGY_IRI not in ontology_declarations


def test_combined_graph_has_exactly_one_ontology_declaration(combined_graph: Graph):
    ontology_declarations = set(combined_graph.subjects(RDF.type, OWL.Ontology))

    assert ontology_declarations == {UAD_ONTOLOGY_IRI}


@pytest.mark.parametrize(
    "class_name",
    [
        "Appraisal",
        "OpinionOfValue",
        "RealProperty",
        "SubjectProperty",
        "Evidence",
        "ValuationApproach",
        "SalesComparisonApproach",
        "CostApproach",
        "IncomeApproach",
        "IndicationOfValue",
        "Reconciliation",
        "ComparableSale",
        "MeasurementRun",
        "Measurement",
    ],
)
def test_required_classes_exist(combined_graph: Graph, class_name: str):
    assert (UAD[class_name], RDF.type, OWL.Class) in combined_graph


@pytest.mark.parametrize(
    "property_name",
    [
        "hasOpinionOfValue",
        "appraisesProperty",
        "usesValuationApproach",
        "producesIndicationOfValue",
        "usesIndicationOfValue",
        "reconcilesToOpinionOfValue",
        "hasReconciliation",
        "usesComparableSale",
        "producedMeasurement",
    ],
)
def test_required_object_properties_exist(combined_graph: Graph, property_name: str):
    assert (UAD[property_name], RDF.type, OWL.ObjectProperty) in combined_graph


def test_every_class_has_label(combined_graph: Graph):
    for class_iri in combined_graph.subjects(RDF.type, OWL.Class):
        assert (class_iri, RDFS.label, None) in combined_graph, (
            f"Missing rdfs:label for {class_iri}"
        )


def test_every_object_property_has_label(combined_graph: Graph):
    for property_iri in combined_graph.subjects(RDF.type, OWL.ObjectProperty):
        assert (property_iri, RDFS.label, None) in combined_graph, (
            f"Missing rdfs:label for {property_iri}"
        )


def test_every_object_property_has_domain(combined_graph: Graph):
    for property_iri in combined_graph.subjects(RDF.type, OWL.ObjectProperty):
        assert (property_iri, RDFS.domain, None) in combined_graph, (
            f"Missing rdfs:domain for {property_iri}"
        )


def test_every_object_property_has_range(combined_graph: Graph):
    for property_iri in combined_graph.subjects(RDF.type, OWL.ObjectProperty):
        assert (property_iri, RDFS.range, None) in combined_graph, (
            f"Missing rdfs:range for {property_iri}"
        )


@pytest.mark.parametrize(
    "class_name",
    [
        "Appraisal",
        "OpinionOfValue",
        "ValuationApproach",
        "IndicationOfValue",
        "Reconciliation",
    ],
)
def test_core_classes_have_skos_definitions(combined_graph: Graph, class_name: str):
    assert (UAD[class_name], SKOS.definition, None) in combined_graph, (
        f"Missing skos:definition for uad:{class_name}"
    )


@pytest.mark.parametrize(
    "section_heading",
    [
        "Appraisal",
        "Opinion of Value",
        "Subject Property",
        "Evidence",
        "Comparable Sale",
        "Measurements",
    ],
)
def test_meaning_model_documents_core_sections(section_heading: str):
    text = MODEL_DOC_FILE.read_text(encoding="utf-8")

    assert f"# {section_heading}" in text