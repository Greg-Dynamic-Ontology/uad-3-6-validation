"""Acceptance tests for IT-7R6S1 complete ontology reconciliation."""

from importlib import import_module
from pathlib import Path

import app
import pytest
from rdflib import Graph, Literal, Namespace, RDF, URIRef

from app.core.schema_source_iri import mint_schema_source_iri
from app.models.schema_model import QName, SchemaModel
from app.services.schema_loader import SchemaLoader


PROJECT_ROOT = Path(app.__file__).resolve().parents[1]
UAD_SCHEMA_FILE = (
    PROJECT_ROOT
    / "specs"
    / "UAD"
    / "GSE_UAD_3.6.0_v1.3"
    / "Combined"
    / "GSE_UAD_3.6.0_v1.3.xsd"
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


@pytest.fixture(scope="module")
def complete_uad_model() -> SchemaModel:
    """Load the complete UAD schema closure once for this scenario."""

    assert UAD_SCHEMA_FILE.is_file(), (
        f"Complete UAD schema entry point not found: {UAD_SCHEMA_FILE}"
    )
    return SchemaLoader().load(UAD_SCHEMA_FILE)


@pytest.fixture(scope="module")
def complete_uad_ontology(complete_uad_model: SchemaModel) -> Graph:
    """Project the complete UAD model once for all reconciliation checks."""

    return _project_to_ontology(complete_uad_model)


def _represented_global_components(
    model: SchemaModel,
) -> tuple[tuple[str, QName], ...]:
    """Return the global component kinds selected for representation."""

    mappings = (
        ("complexType", model.complex_types),
        ("simpleType", model.simple_types),
        ("element", model.elements),
        ("attribute", model.attributes),
        ("attributeGroup", model.attribute_groups),
        ("group", model.model_groups),
    )

    return tuple(
        (component_kind, qname)
        for component_kind, components in mappings
        for qname in components
    )


def _schema_components_for(
    graph: Graph,
    component_kind: str,
    qname: QName,
) -> set[URIRef]:
    """Find projected schema resources by their governed source evidence."""

    return {
        component
        for component in graph.subjects(
            UAD_SCHEMA.sourceQName,
            Literal(qname.clark_name),
        )
        if isinstance(component, URIRef)
        and (
            component,
            UAD_SCHEMA.componentKind,
            Literal(component_kind),
        ) in graph
    }


def test_every_represented_global_component_has_one_disposition(
    complete_uad_model: SchemaModel,
    complete_uad_ontology: Graph,
) -> None:
    """Every represented global component is projected or unresolved."""

    represented_components = _represented_global_components(
        complete_uad_model
    )
    assert represented_components

    for component_kind, qname in represented_components:
        schema_components = _schema_components_for(
            complete_uad_ontology,
            component_kind,
            qname,
        )
        assert len(schema_components) == 1, (
            f"Expected one schema resource for {component_kind} "
            f"{qname.clark_name}; found {len(schema_components)}."
        )

        schema_component = next(iter(schema_components))
        dispositions = tuple(
            complete_uad_ontology.objects(
                schema_component,
                UAD_SCHEMA.projectionDisposition,
            )
        )
        assert len(dispositions) == 1, (
            f"Expected one projection disposition for {component_kind} "
            f"{qname.clark_name}; found {len(dispositions)}."
        )
        assert str(dispositions[0]) in {"projected", "unresolved"}


def test_every_projected_term_identifies_its_schema_component(
    complete_uad_ontology: Graph,
) -> None:
    """Every projected term links back to exactly one schema resource."""

    projected_components = {
        component
        for component in complete_uad_ontology.subjects(
            UAD_SCHEMA.projectionDisposition,
            Literal("projected"),
        )
        if isinstance(component, URIRef)
    }
    assert projected_components

    for schema_component in projected_components:
        ontology_terms = tuple(
            complete_uad_ontology.objects(
                schema_component,
                UAD_SCHEMA.projectsTo,
            )
        )
        assert len(ontology_terms) == 1
        assert (
            ontology_terms[0],
            PROV.wasDerivedFrom,
            schema_component,
        ) in complete_uad_ontology


def test_every_discovered_occurrence_has_one_projection_disposition(
    complete_uad_model: SchemaModel,
    complete_uad_ontology: Graph,
) -> None:
    """Every discovered XSD occurrence is reconciled exactly once."""

    source_documents = {
        disposition.source_document
        for disposition in complete_uad_model.processing_dispositions
    }
    source_iris = {
        source_document: mint_schema_source_iri(source_document)
        for source_document in source_documents
    }
    expected_occurrences = {
        (
            disposition.component_kind,
            disposition.source_index,
            source_iris[disposition.source_document],
        )
        for disposition in complete_uad_model.processing_dispositions
    }
    assert len(expected_occurrences) == len(
        complete_uad_model.processing_dispositions
    )

    disposition_resources = set(
        complete_uad_ontology.subjects(
            RDF.type,
            UAD_SCHEMA.OntologyProjectionDisposition,
        )
    )
    assert len(disposition_resources) == len(expected_occurrences)

    actual_occurrences: set[tuple[str, int, URIRef]] = set()
    for resource in disposition_resources:
        component_kinds = tuple(
            complete_uad_ontology.objects(
                resource,
                UAD_SCHEMA.componentKind,
            )
        )
        source_indexes = tuple(
            complete_uad_ontology.objects(
                resource,
                UAD_SCHEMA.sourceIndex,
            )
        )
        source_documents = tuple(
            complete_uad_ontology.objects(
                resource,
                UAD_SCHEMA.sourceDocument,
            )
        )
        actions = tuple(
            complete_uad_ontology.objects(
                resource,
                UAD_SCHEMA.projectionAction,
            )
        )

        assert len(component_kinds) == 1
        assert len(source_indexes) == 1
        assert len(source_documents) == 1
        assert len(actions) == 1

        action = str(actions[0])
        assert action in {"projected", "excluded", "unresolved"}

        if action == "excluded":
            governing_decisions = tuple(
                complete_uad_ontology.objects(
                    resource,
                    UAD_SCHEMA.governingDecision,
                )
            )
            assert len(governing_decisions) == 1

        source_document = source_documents[0]
        assert isinstance(source_document, URIRef)
        actual_occurrences.add(
            (
                str(component_kinds[0]),
                int(source_indexes[0]),
                source_document,
            )
        )

    assert actual_occurrences == expected_occurrences
