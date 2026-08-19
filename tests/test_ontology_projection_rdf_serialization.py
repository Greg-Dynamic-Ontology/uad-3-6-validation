"""Acceptance test for IT-7R5S1 valid RDF serialization."""

from importlib import import_module
from pathlib import Path

import pytest
from rdflib import Graph, Namespace, RDF
from rdflib.namespace import OWL

from app.models.schema_model import (
    ComplexTypeDefinition,
    QName,
    SchemaModel,
)


MISMO_SOURCE_NAMESPACE = (
    "http://www.mismo.org/residential/2009/schemas"
)
MISMO_ONTOLOGY = Namespace(
    "https://dynamicontology.com/mismo/ontology#"
)


def _projection_module() -> object:
    """Load the public Logical Schema Model projection module."""

    module_name = "app.projections.logical_schema_to_ontology"

    try:
        return import_module(module_name)
    except ModuleNotFoundError as error:
        if error.name != module_name:
            raise
        pytest.fail(
            "Logical Schema Model ontology projection is not yet "
            f"implemented: expected module {module_name}."
        )


def test_projected_ontology_serializes_as_valid_turtle(
    tmp_path: Path,
) -> None:
    """IT-7R5S1: Projected Turtle reparses as the expected RDF graph."""

    module = _projection_module()
    serialize = getattr(
        module,
        "serialize_logical_schema_ontology",
        None,
    )
    assert callable(serialize), (
        "logical_schema_to_ontology must provide "
        "serialize_logical_schema_ontology()."
    )

    type_name = QName(MISMO_SOURCE_NAMESPACE, "PropertyType")
    model = SchemaModel(
        target_namespace=MISMO_SOURCE_NAMESPACE,
        complex_types={
            type_name: ComplexTypeDefinition(name=type_name),
        },
    )
    output_file = tmp_path / "mismo-ontology.ttl"

    serialized_file = serialize(model, output_file)

    assert serialized_file == output_file
    assert output_file.is_file()
    assert output_file.stat().st_size > 0

    reparsed_graph = Graph()
    reparsed_graph.parse(output_file, format="turtle")

    assert len(reparsed_graph) > 0
    assert (
        MISMO_ONTOLOGY.Property,
        RDF.type,
        OWL.Class,
    ) in reparsed_graph
