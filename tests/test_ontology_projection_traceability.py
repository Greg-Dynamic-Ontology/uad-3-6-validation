"""Acceptance test for IT-7R4S1 ontology projection traceability."""

from dataclasses import fields
from hashlib import sha256
from importlib import import_module
from pathlib import Path

import pytest
from rdflib import Graph, Literal, Namespace, RDF, URIRef

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
UAD_SCHEMA = Namespace(
    "https://dynamicontology.com/uad36/schema#"
)
PROV = Namespace("http://www.w3.org/ns/prov#")
SCHEMA_SOURCE_IRI_PREFIX = (
    "https://dynamicontology.com/uad36/source/sha256/"
)

SCHEMA_BYTES = b"""<?xml version="1.0" encoding="UTF-8"?>
<xs:schema
    xmlns:xs="http://www.w3.org/2001/XMLSchema"
    targetNamespace="http://www.mismo.org/residential/2009/schemas">
  <xs:complexType name="PropertyType"/>
</xs:schema>
"""


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


def test_projection_preserves_component_source_traceability(
    tmp_path: Path,
) -> None:
    """IT-7R4S1: Link ontology term, component, and source document."""

    definition_fields = {
        field.name
        for field in fields(ComplexTypeDefinition)
    }
    assert "source_document" in definition_fields, (
        "ComplexTypeDefinition must preserve the source_document needed "
        "for ontology-projection traceability."
    )

    source_document = tmp_path / "property.xsd"
    source_document.write_bytes(SCHEMA_BYTES)

    type_name = QName(MISMO_SOURCE_NAMESPACE, "PropertyType")
    complex_type = ComplexTypeDefinition(
        name=type_name,
        source_document=source_document,
    )
    model = SchemaModel(
        target_namespace=MISMO_SOURCE_NAMESPACE,
        complex_types={type_name: complex_type},
    )

    graph = _project_to_ontology(model)

    ontology_term = MISMO_ONTOLOGY.Property
    schema_component = UAD_SCHEMA["complexType-PropertyType"]
    digest = sha256(SCHEMA_BYTES).hexdigest()
    source_iri = URIRef(SCHEMA_SOURCE_IRI_PREFIX + digest)

    assert (
        ontology_term,
        PROV.wasDerivedFrom,
        schema_component,
    ) in graph
    assert (
        schema_component,
        PROV.wasDerivedFrom,
        source_iri,
    ) in graph
    assert (
        source_iri,
        RDF.type,
        UAD_SCHEMA.SchemaSourceDocument,
    ) in graph
    assert (
        source_iri,
        UAD_SCHEMA.contentDigest,
        Literal(digest),
    ) in graph

    assert not any(
        str(tmp_path) in str(term)
        for term in _uri_terms(graph)
    ), "A physical source location must not contribute to a governed IRI."
