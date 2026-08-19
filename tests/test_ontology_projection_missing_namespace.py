"""Acceptance test for IT-7R3S2 missing source namespace handling."""

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
MISMO_ONTOLOGY = Namespace(
    "https://dynamicontology.com/mismo/ontology#"
)
UAD_ONTOLOGY = Namespace(
    "https://dynamicontology.com/uad36/ontology#"
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


def test_missing_target_namespace_preserves_mismo_ontology_authority() -> None:
    """IT-7R3S2: Missing source namespace does not change authority."""

    type_name = QName(MISMO_SOURCE_NAMESPACE, "PropertyType")
    model = SchemaModel(
        target_namespace=None,
        complex_types={
            type_name: ComplexTypeDefinition(name=type_name),
        },
    )

    graph = _project_to_ontology(model)

    assert (MISMO_ONTOLOGY.Property, RDF.type, OWL.Class) in graph
    assert (UAD_ONTOLOGY.Property, RDF.type, OWL.Class) not in graph

    reconciliations = set(
        graph.subjects(
            RDF.type,
            UAD_SCHEMA.OntologyProjectionReconciliation,
        )
    )
    assert len(reconciliations) == 1

    reconciliation = next(iter(reconciliations))
    assert isinstance(reconciliation, URIRef)
    assert (
        reconciliation,
        UAD_SCHEMA.sourceTargetNamespaceStatus,
        Literal("missing"),
    ) in graph
    assert (
        reconciliation,
        UAD_SCHEMA.ontologyAuthority,
        URIRef(str(MISMO_ONTOLOGY)),
    ) in graph
