"""Acceptance test for IT-7R3S3 deterministic ontology identities."""

from importlib import import_module

import pytest
from rdflib import Graph, Namespace, URIRef

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


def _model_with_component_order(
    names: tuple[QName, ...],
) -> SchemaModel:
    """Construct one logical model using the supplied insertion order."""

    return SchemaModel(
        target_namespace=MISMO_SOURCE_NAMESPACE,
        complex_types={
            name: ComplexTypeDefinition(name=name)
            for name in names
        },
    )


def _iri_set(graph: Graph) -> frozenset[URIRef]:
    """Return every IRI appearing anywhere in a projected graph."""

    return frozenset(
        term
        for triple in graph
        for term in triple
        if isinstance(term, URIRef)
    )


def test_repeated_projection_produces_the_same_iris() -> None:
    """IT-7R3S3: Equivalent projections produce identical IRI sets."""

    property_type = QName(MISMO_SOURCE_NAMESPACE, "PropertyType")
    address_type = QName(MISMO_SOURCE_NAMESPACE, "AddressType")
    external_type = QName(XLINK_SOURCE_NAMESPACE, "ForeignType")

    first_model = _model_with_component_order(
        (property_type, address_type, external_type)
    )
    equivalent_model = _model_with_component_order(
        (external_type, address_type, property_type)
    )

    first_iris = _iri_set(_project_to_ontology(first_model))
    repeated_iris = _iri_set(_project_to_ontology(first_model))
    reordered_iris = _iri_set(_project_to_ontology(equivalent_model))

    assert MISMO_ONTOLOGY.Property in first_iris
    assert MISMO_ONTOLOGY.Address in first_iris
    assert UAD_SCHEMA["ontology-projection-reconciliation"] in first_iris
    assert any(
        str(iri).startswith(str(UAD_SCHEMA))
        and "complexType-" in str(iri)
        for iri in first_iris
    )

    assert repeated_iris == first_iris
    assert reordered_iris == first_iris
