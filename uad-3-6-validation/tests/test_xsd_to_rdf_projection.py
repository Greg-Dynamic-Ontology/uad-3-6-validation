from pathlib import Path

from rdflib import Graph, RDF, RDFS, URIRef
from rdflib.compare import graph_diff, isomorphic
from rdflib.namespace import OWL

from app.projections.xsd_to_rdf import project_xsd_to_rdf


PROJECT_ROOT = Path(__file__).resolve().parents[1]

INPUT_XSD = (
    PROJECT_ROOT
    / "examples"
    / "xsd"
    / "complexType-element.xsd"
)

EXPECTED_RDF = (
    PROJECT_ROOT
    / "examples"
    / "rdf"
    / "complexType-element.ttl"
)

NAMESPACED_INPUT_XSD = (
    PROJECT_ROOT
    / "examples"
    / "xsd"
    / "complexType-element-ns.xsd"
)

NAMESPACED_EXPECTED_RDF = (
    PROJECT_ROOT
    / "examples"
    / "rdf"
    / "complexType-element-ns.ttl"
)

TARGET_NAMESPACE = (
    "https://dynamicontology.com/otdd/examples/complexType-element#"
)

NAMESPACED_TARGET_NAMESPACE = (
    "https://dynamicontology.com/otdd/examples#"
)

ADDRESS_TYPE_IRI = URIRef(
    f"{TARGET_NAMESPACE}AddressType"
)

ADDRESS_IRI = URIRef(
    f"{TARGET_NAMESPACE}Address"
)

NAMESPACED_ADDRESS_TYPE_IRI = URIRef(
    f"{NAMESPACED_TARGET_NAMESPACE}AddressType"
)

NAMESPACED_ADDRESS_IRI = URIRef(
    f"{NAMESPACED_TARGET_NAMESPACE}Address"
)


def test_projection_returns_an_rdflib_graph() -> None:
    actual_graph = project_xsd_to_rdf(INPUT_XSD)

    assert isinstance(actual_graph, Graph), (
        "project_xsd_to_rdf() must return an rdflib.Graph; "
        f"received {type(actual_graph).__name__}."
    )


def test_projection_contains_an_owl_class() -> None:
    actual_graph = project_xsd_to_rdf(INPUT_XSD)

    owl_classes = list(
        actual_graph.subjects(
            predicate=RDF.type,
            object=OWL.Class,
        )
    )

    assert owl_classes, (
        "The projected graph must contain at least one resource "
        "declared as an owl:Class."
    )


def test_complex_type_projects_to_expected_owl_class() -> None:
    actual_graph = project_xsd_to_rdf(INPUT_XSD)

    expected_triple = (
        ADDRESS_TYPE_IRI,
        RDF.type,
        OWL.Class,
    )

    assert expected_triple in actual_graph, (
        "The global xsd:complexType named AddressType must project "
        f"to <{ADDRESS_TYPE_IRI}> a owl:Class."
    )


def test_element_projects_to_expected_object_property() -> None:
    actual_graph = project_xsd_to_rdf(INPUT_XSD)

    expected_triple = (
        ADDRESS_IRI,
        RDF.type,
        OWL.ObjectProperty,
    )

    assert expected_triple in actual_graph, (
        "The global xsd:element named Address must project to "
        f"<{ADDRESS_IRI}> a owl:ObjectProperty."
    )


def test_element_type_projects_to_expected_range() -> None:
    actual_graph = project_xsd_to_rdf(INPUT_XSD)

    expected_triple = (
        ADDRESS_IRI,
        RDFS.range,
        ADDRESS_TYPE_IRI,
    )

    assert expected_triple in actual_graph, (
        "The Address element's type reference to AddressType must "
        f"project to rdfs:range <{ADDRESS_TYPE_IRI}>."
    )


def test_projection_uses_fallback_namespace_when_target_namespace_is_absent() -> None:
    actual_graph = project_xsd_to_rdf(INPUT_XSD)

    generated_subjects = {
        subject
        for subject in actual_graph.subjects()
        if isinstance(subject, URIRef)
    }

    assert generated_subjects, (
        "The projection must generate at least one URI subject."
    )

    unexpected_subjects = {
        subject
        for subject in generated_subjects
        if not str(subject).startswith(TARGET_NAMESPACE)
    }

    assert not unexpected_subjects, (
        "When the XSD has no targetNamespace, generated resources "
        "must use the configured fallback namespace.\n"
        f"Expected namespace: {TARGET_NAMESPACE}\n"
        f"Unexpected subjects: "
        f"{sorted(map(str, unexpected_subjects))}"
    )


def test_complex_type_and_element_projection_matches_expected_rdf() -> None:
    actual_graph = project_xsd_to_rdf(INPUT_XSD)

    assert isinstance(actual_graph, Graph), (
        "project_xsd_to_rdf() must return an rdflib.Graph; "
        f"received {type(actual_graph).__name__}."
    )

    expected_graph = Graph()
    expected_graph.parse(
        EXPECTED_RDF,
        format="turtle",
    )

    if not isomorphic(actual_graph, expected_graph):
        _, only_in_actual, only_in_expected = graph_diff(
            actual_graph,
            expected_graph,
        )

        raise AssertionError(
            "The projected RDF graph is not semantically equivalent "
            "to the expected graph.\n\n"
            "Only in actual graph:\n"
            f"{only_in_actual.serialize(format='turtle')}\n"
            "Only in expected graph:\n"
            f"{only_in_expected.serialize(format='turtle')}"
        )


def test_namespaced_global_element_projects_to_expected_rdf() -> None:
    actual_graph = project_xsd_to_rdf(NAMESPACED_INPUT_XSD)

    expected_graph = Graph()
    expected_graph.parse(
        NAMESPACED_EXPECTED_RDF,
        format="turtle",
    )

    if not isomorphic(actual_graph, expected_graph):
        _, only_in_actual, only_in_expected = graph_diff(
            actual_graph,
            expected_graph,
        )

        raise AssertionError(
            "A global xsd:element whose type is expressed as the "
            "QName tns:AddressType must project using the XSD "
            "targetNamespace.\n\n"
            "Only in actual graph:\n"
            f"{only_in_actual.serialize(format='turtle')}\n"
            "Only in expected graph:\n"
            f"{only_in_expected.serialize(format='turtle')}"
        )