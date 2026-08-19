"""Acceptance test for IT-7R5S2 duplicate-triple prevention."""

from collections import Counter
from importlib import import_module

import pytest
from rdflib import Graph, Namespace, RDF
from rdflib.namespace import OWL

from app.models.schema_model import (
    ComplexTypeDefinition,
    ElementDeclaration,
    QName,
    SchemaModel,
)


MISMO_SOURCE_NAMESPACE = (
    "http://www.mismo.org/residential/2009/schemas"
)
MISMO_ONTOLOGY = Namespace(
    "https://dynamicontology.com/mismo/ontology#"
)


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


def test_repeated_component_references_do_not_duplicate_triples() -> None:
    """IT-7R5S2: Repeated references retain RDF set semantics."""

    property_type = QName(MISMO_SOURCE_NAMESPACE, "PropertyType")
    subject_property = QName(
        MISMO_SOURCE_NAMESPACE,
        "SubjectProperty",
    )
    comparable_property = QName(
        MISMO_SOURCE_NAMESPACE,
        "ComparableProperty",
    )

    model = SchemaModel(
        target_namespace=MISMO_SOURCE_NAMESPACE,
        complex_types={
            property_type: ComplexTypeDefinition(name=property_type),
        },
        elements={
            subject_property: ElementDeclaration(
                name=subject_property,
                type_name=property_type,
            ),
            comparable_property: ElementDeclaration(
                name=comparable_property,
                type_name=property_type,
            ),
        },
    )

    graph = _project_to_ontology(model)
    class_triple = (
        MISMO_ONTOLOGY.Property,
        RDF.type,
        OWL.Class,
    )

    assert class_triple in graph
    assert list(graph.triples(class_triple)) == [class_triple]

    triple_counts = Counter(graph)
    assert triple_counts
    assert all(count == 1 for count in triple_counts.values())
