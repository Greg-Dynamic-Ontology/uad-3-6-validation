"""Acceptance tests for IT-7R3S1 governed ontology identities."""

from importlib import import_module

import pytest
from rdflib import Graph, Literal, Namespace, RDF, URIRef
from rdflib.namespace import OWL

from app.models.schema_model import (
    ComplexTypeDefinition,
    QName,
    SchemaModel,
)


MISMO_SOURCE_NAMESPACE = (
    "http://www.mismo.org/residential/2009/schemas"
)
XLINK_SOURCE_NAMESPACE = "http://www.w3.org/1999/xlink"

MISMO_ONTOLOGY = Namespace(
    "https://dynamicontology.com/mismo/ontology#"
)
UAD_SCHEMA = Namespace(
    "https://dynamicontology.com/uad36/schema#"
)
PROV = Namespace("http://www.w3.org/ns/prov#")


def _project_to_ontology(model: SchemaModel) -> Graph:
    """Call the public Logical Schema Model projection entry point."""

    module_name = "app.projections.logical_schema_to_ontology"

    try:
        module = import_module(module_name)
    except ModuleNotFoundError as error:
        if error.name != module_name:
            raise
        pytest.fail(
            "Logical Schema Model ontology projection is not yet "
            f"implemented: expected module {module_name}."
        )

    projector = getattr(
        module,
        "project_logical_schema_to_ontology",
        None,
    )
    assert callable(projector), (
        "logical_schema_to_ontology must provide "
        "project_logical_schema_to_ontology()."
    )

    graph = projector(model)
    assert isinstance(graph, Graph), (
        "project_logical_schema_to_ontology() must return an rdflib.Graph."
    )
    return graph


def _uri_terms(graph: Graph) -> set[URIRef]:
    """Return every URI used as a subject, predicate, or object."""

    return {
        term
        for triple in graph
        for term in triple
        if isinstance(term, URIRef)
    }


def test_projection_separates_schema_and_mismo_ontology_identities() -> None:
    """IT-7R3S1: Use governed, distinct, and linked IRIs."""

    type_name = QName(MISMO_SOURCE_NAMESPACE, "PropertyType")
    model = SchemaModel(
        target_namespace=MISMO_SOURCE_NAMESPACE,
        complex_types={
            type_name: ComplexTypeDefinition(name=type_name),
        },
    )

    graph = _project_to_ontology(model)

    schema_component = UAD_SCHEMA["complexType-PropertyType"]
    ontology_term = MISMO_ONTOLOGY.Property

    assert schema_component != ontology_term
    assert (ontology_term, RDF.type, OWL.Class) in graph
    assert (
        schema_component,
        RDF.type,
        UAD_SCHEMA.ComplexType,
    ) in graph
    assert (
        ontology_term,
        PROV.wasDerivedFrom,
        schema_component,
    ) in graph
    assert (
        schema_component,
        UAD_SCHEMA.sourceNamespace,
        Literal(MISMO_SOURCE_NAMESPACE),
    ) in graph
    assert (
        schema_component,
        UAD_SCHEMA.sourceLocalName,
        Literal("PropertyType"),
    ) in graph
    assert (
        schema_component,
        UAD_SCHEMA.componentKind,
        Literal("complexType"),
    ) in graph

    assert not any(
        str(term).startswith(MISMO_SOURCE_NAMESPACE)
        for term in _uri_terms(graph)
    ), "The XML Schema target namespace must remain provenance, not authority."


def test_component_without_mismo_mapping_remains_unresolved() -> None:
    """IT-7R3S1: Do not invent a domain term for an external component."""

    type_name = QName(XLINK_SOURCE_NAMESPACE, "ForeignType")
    model = SchemaModel(
        target_namespace=MISMO_SOURCE_NAMESPACE,
        complex_types={
            type_name: ComplexTypeDefinition(name=type_name),
        },
    )

    graph = _project_to_ontology(model)

    unresolved_components = {
        component
        for component in graph.subjects(
            UAD_SCHEMA.projectionDisposition,
            Literal("unresolved"),
        )
        if (
            component,
            UAD_SCHEMA.sourceNamespace,
            Literal(XLINK_SOURCE_NAMESPACE),
        ) in graph
    }

    assert len(unresolved_components) == 1
    unresolved_component = next(iter(unresolved_components))
    assert isinstance(unresolved_component, URIRef)
    assert str(unresolved_component).startswith(str(UAD_SCHEMA))
    assert (
        MISMO_ONTOLOGY.Foreign,
        RDF.type,
        OWL.Class,
    ) not in graph
