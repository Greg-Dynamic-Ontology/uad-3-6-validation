"""Project the UAD Logical Schema Model into the shared MISMO ontology."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from rdflib import Graph, Literal, Namespace, RDF, URIRef
from rdflib.namespace import OWL

from app.core.schema_source_iri import mint_schema_source_iri
from app.generators.complex_type_vocabulary import (
    class_name_from_type_name,
    local_name_from_text,
)
from app.models.schema_model import QName, SchemaModel


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
MINTING_POLICY_VERSION = "ADR-0017"
RECONCILIATION_IRI = UAD_SCHEMA["ontology-projection-reconciliation"]


def _namespace_discriminator(namespace: str | None) -> str:
    """Return a stable qualifier for a non-primary source namespace."""

    value = "" if namespace is None else namespace
    return sha256(value.encode("utf-8")).hexdigest()[:12]


def _complex_type_component_iri(
    model: SchemaModel,
    name: QName,
) -> URIRef:
    """Mint the governed schema-component IRI for a complex type."""

    local_token = local_name_from_text(name.local_name)
    component_token = f"complexType-{local_token}"

    if name.namespace != model.target_namespace:
        qualifier = _namespace_discriminator(name.namespace)
        component_token = f"namespace-{qualifier}-{component_token}"

    return UAD_SCHEMA[component_token]


def _record_schema_component(
    graph: Graph,
    component_iri: URIRef,
    name: QName,
) -> None:
    """Record the identity evidence shared by all complex types."""

    graph.add((component_iri, RDF.type, UAD_SCHEMA.ComplexType))
    graph.add(
        (
            component_iri,
            UAD_SCHEMA.componentKind,
            Literal("complexType"),
        )
    )
    graph.add(
        (
            component_iri,
            UAD_SCHEMA.sourceLocalName,
            Literal(name.local_name),
        )
    )
    graph.add(
        (
            component_iri,
            UAD_SCHEMA.sourceQName,
            Literal(name.clark_name),
        )
    )
    graph.add(
        (
            component_iri,
            UAD_SCHEMA.mintingPolicyVersion,
            Literal(MINTING_POLICY_VERSION),
        )
    )

    if name.namespace is not None:
        graph.add(
            (
                component_iri,
                UAD_SCHEMA.sourceNamespace,
                Literal(name.namespace),
            )
        )


def _record_source_document_traceability(
    graph: Graph,
    component_iri: URIRef,
    source_document: Path,
) -> None:
    """Link a schema component to its governed source artifact."""

    source_iri = mint_schema_source_iri(source_document)
    digest = sha256(source_document.read_bytes()).hexdigest()

    graph.add((component_iri, PROV.wasDerivedFrom, source_iri))
    graph.add(
        (
            source_iri,
            RDF.type,
            UAD_SCHEMA.SchemaSourceDocument,
        )
    )
    graph.add(
        (
            source_iri,
            UAD_SCHEMA.contentDigest,
            Literal(digest),
        )
    )


def _project_mismo_complex_type(
    graph: Graph,
    component_iri: URIRef,
    name: QName,
) -> None:
    """Project one governed MISMO complex type to an OWL class."""

    class_name = class_name_from_type_name(name.local_name)
    ontology_iri = MISMO_ONTOLOGY[local_name_from_text(class_name)]

    graph.add((ontology_iri, RDF.type, OWL.Class))
    graph.add((ontology_iri, PROV.wasDerivedFrom, component_iri))
    graph.add((component_iri, UAD_SCHEMA.projectsTo, ontology_iri))
    graph.add(
        (
            component_iri,
            UAD_SCHEMA.projectionDisposition,
            Literal("projected"),
        )
    )
    graph.add(
        (
            ontology_iri,
            UAD_SCHEMA.mintingPolicyVersion,
            Literal(MINTING_POLICY_VERSION),
        )
    )


def _record_projection_reconciliation(
    graph: Graph,
    model: SchemaModel,
) -> None:
    """Record source-namespace status without changing ontology authority."""

    graph.add(
        (
            RECONCILIATION_IRI,
            RDF.type,
            UAD_SCHEMA.OntologyProjectionReconciliation,
        )
    )
    graph.add(
        (
            RECONCILIATION_IRI,
            UAD_SCHEMA.ontologyAuthority,
            URIRef(str(MISMO_ONTOLOGY)),
        )
    )

    if model.target_namespace is None:
        graph.add(
            (
                RECONCILIATION_IRI,
                UAD_SCHEMA.sourceTargetNamespaceStatus,
                Literal("missing"),
            )
        )
    else:
        graph.add(
            (
                RECONCILIATION_IRI,
                UAD_SCHEMA.sourceTargetNamespaceStatus,
                Literal("present"),
            )
        )
        graph.add(
            (
                RECONCILIATION_IRI,
                UAD_SCHEMA.sourceTargetNamespace,
                Literal(model.target_namespace),
            )
        )


def project_logical_schema_to_ontology(model: SchemaModel) -> Graph:
    """Project represented UAD schema components into MISMO ontology terms."""

    graph = Graph()
    graph.bind("mismo", MISMO_ONTOLOGY)
    graph.bind("uadschema", UAD_SCHEMA)
    graph.bind("prov", PROV)
    graph.bind("owl", OWL)

    _record_projection_reconciliation(graph, model)

    for complex_type in model.complex_types.values():
        component_iri = _complex_type_component_iri(
            model,
            complex_type.name,
        )
        _record_schema_component(
            graph,
            component_iri,
            complex_type.name,
        )
        if complex_type.source_document is not None:
            _record_source_document_traceability(
                graph,
                component_iri,
                complex_type.source_document,
            )

        if complex_type.name.namespace == MISMO_SOURCE_NAMESPACE:
            _project_mismo_complex_type(
                graph,
                component_iri,
                complex_type.name,
            )
        else:
            graph.add(
                (
                    component_iri,
                    UAD_SCHEMA.projectionDisposition,
                    Literal("unresolved"),
                )
            )

    return graph


__all__ = [
    "MINTING_POLICY_VERSION",
    "MISMO_ONTOLOGY",
    "MISMO_SOURCE_NAMESPACE",
    "PROV",
    "RECONCILIATION_IRI",
    "UAD_SCHEMA",
    "project_logical_schema_to_ontology",
]
