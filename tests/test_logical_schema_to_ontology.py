"""Acceptance test for IT-7R1S1 Logical Schema Model projection."""

from importlib import import_module

import pytest
from rdflib import Graph, Namespace, RDF
from rdflib.namespace import OWL

from app.models.schema_model import (
    ComplexTypeDefinition,
    QName,
    SchemaModel,
)


MISMO_NAMESPACE = "http://www.mismo.org/residential/2009/schemas"
MISMO_ONTOLOGY = Namespace(
    "https://dynamicontology.com/mismo/ontology#"
)


def _project_to_ontology(model: SchemaModel) -> Graph:
    """Call the required public projection entry point."""

    module_name = "app.projections.logical_schema_to_ontology"

    try:
        module = import_module(module_name)
    except ModuleNotFoundError as error:
        if error.name != module_name:
            raise
        pytest.fail(
            "Logical Schema Model ontology projection is not yet "
            "implemented: expected module "
            f"{module_name}."
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


def test_named_complex_type_projects_to_owl_class() -> None:
    """A named complex type becomes its governed MISMO OWL class."""

    type_name = QName(MISMO_NAMESPACE, "PropertyType")
    model = SchemaModel(
        target_namespace=MISMO_NAMESPACE,
        complex_types={
            type_name: ComplexTypeDefinition(name=type_name),
        },
    )

    graph = _project_to_ontology(model)

    assert (MISMO_ONTOLOGY.Property, RDF.type, OWL.Class) in graph
