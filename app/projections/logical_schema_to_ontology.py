"""Project the UAD Logical Schema Model into the shared MISMO ontology."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from rdflib import Graph, Literal, Namespace, RDF, RDFS, URIRef, XSD
from rdflib.namespace import OWL, SKOS

from app.core.schema_source_iri import mint_schema_source_iri
from app.generators.complex_type_vocabulary import (
    class_name_from_type_name,
    local_name_from_text,
)
from app.models.schema_model import (
    AttributeDeclaration,
    ElementDeclaration,
    ModelGroup,
    ModelGroupReference,
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
MINTING_POLICY_VERSION = "ADR-0017"
RECONCILIATION_IRI = UAD_SCHEMA["ontology-projection-reconciliation"]


def _namespace_discriminator(namespace: str | None) -> str:
    """Return a stable qualifier for a non-primary source namespace."""

    value = "" if namespace is None else namespace
    return sha256(value.encode("utf-8")).hexdigest()[:12]


def _schema_component_iri(
    model: SchemaModel,
    component_kind: str,
    name: QName,
) -> URIRef:
    """Mint a governed IRI for one global schema component."""

    local_token = local_name_from_text(name.local_name)
    component_token = f"{component_kind}-{local_token}"

    if name.namespace != model.target_namespace:
        qualifier = _namespace_discriminator(name.namespace)
        component_token = f"namespace-{qualifier}-{component_token}"

    return UAD_SCHEMA[component_token]


def _record_schema_component(
    graph: Graph,
    component_iri: URIRef,
    name: QName,
    component_kind: str,
) -> None:
    """Record identity evidence shared by global schema components."""

    component_classes = {
        "attribute": UAD_SCHEMA.AttributeDeclaration,
        "attributeGroup": UAD_SCHEMA.AttributeGroup,
        "complexType": UAD_SCHEMA.ComplexType,
        "element": UAD_SCHEMA.ElementDeclaration,
        "group": UAD_SCHEMA.ModelGroup,
        "simpleType": UAD_SCHEMA.SimpleType,
    }
    graph.add(
        (
            component_iri,
            RDF.type,
            component_classes[component_kind],
        )
    )
    graph.add(
        (
            component_iri,
            UAD_SCHEMA.componentKind,
            Literal(component_kind),
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
    source_identities: dict[Path, tuple[URIRef, str]],
) -> None:
    """Link a schema component to its governed source artifact."""

    source_iri, digest = _source_identity(
        source_document,
        source_identities,
    )

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


def _source_identity(
    source_document: Path,
    source_identities: dict[Path, tuple[URIRef, str]],
) -> tuple[URIRef, str]:
    """Return one cached governed source identity and its digest."""

    resolved_document = source_document.resolve()
    identity = source_identities.get(resolved_document)

    if identity is None:
        source_iri = mint_schema_source_iri(resolved_document)
        digest = str(source_iri).rsplit("/", 1)[-1]
        identity = (source_iri, digest)
        source_identities[resolved_document] = identity

    return identity


def _record_occurrence_dispositions(
    graph: Graph,
    model: SchemaModel,
    source_identities: dict[Path, tuple[URIRef, str]],
) -> None:
    """Reconcile every discovered XSD occurrence exactly once."""

    for disposition in model.processing_dispositions:
        source_iri, _ = _source_identity(
            disposition.source_document,
            source_identities,
        )
        semantic_key = "|".join(
            (
                str(source_iri),
                str(disposition.source_index),
                disposition.component_kind,
            )
        )
        digest = sha256(semantic_key.encode("utf-8")).hexdigest()
        resource = UAD_SCHEMA[f"projection-disposition-{digest}"]

        action = (
            "excluded"
            if disposition.action == "ignore"
            else "unresolved"
        )

        graph.add(
            (
                resource,
                RDF.type,
                UAD_SCHEMA.OntologyProjectionDisposition,
            )
        )
        graph.add(
            (
                resource,
                UAD_SCHEMA.componentKind,
                Literal(disposition.component_kind),
            )
        )
        graph.add(
            (
                resource,
                UAD_SCHEMA.sourceIndex,
                Literal(disposition.source_index),
            )
        )
        graph.add(
            (
                resource,
                UAD_SCHEMA.sourceDocument,
                source_iri,
            )
        )
        graph.add(
            (
                resource,
                UAD_SCHEMA.projectionAction,
                Literal(action),
            )
        )
        graph.add(
            (
                resource,
                UAD_SCHEMA.governingDecision,
                Literal(disposition.governing_decision),
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


def _ontology_term(name: QName) -> URIRef:
    """Return the governed shared-MISMO term for a schema name."""

    return MISMO_ONTOLOGY[local_name_from_text(name.local_name)]


def _type_term(
    graph: Graph,
    model: SchemaModel,
    type_name: QName | None,
) -> tuple[URIRef, str]:
    """Resolve one XML Schema type to its governed RDF range."""

    if type_name is None:
        return XSD.string, "datatype"

    if type_name.namespace == "http://www.w3.org/2001/XMLSchema":
        return XSD[type_name.local_name], "datatype"

    if type_name in model.complex_types:
        class_name = class_name_from_type_name(type_name.local_name)
        term = MISMO_ONTOLOGY[local_name_from_text(class_name)]
        graph.add((term, RDF.type, OWL.Class))
        return term, "class"

    controlled_type = _controlled_type(model, type_name)
    if controlled_type is not None:
        return SKOS.Concept, "controlled"

    term = _ontology_term(type_name)
    graph.add((term, RDF.type, RDFS.Datatype))
    return term, "datatype"


def _controlled_type(
    model: SchemaModel,
    type_name: QName | None,
    visited: frozenset[QName] = frozenset(),
) -> QName | None:
    """Find the enumerated base of a simple-type derivation chain."""

    if type_name is None or type_name in visited:
        return None
    definition = model.simple_types.get(type_name)
    if definition is None:
        return None
    if definition.enumeration_values:
        return type_name
    return _controlled_type(
        model,
        definition.base_type,
        visited | {type_name},
    )


def _project_enumeration(
    graph: Graph,
    simple_type_name: QName,
    values: tuple[str, ...],
) -> URIRef:
    """Project a simple-type enumeration as a governed concept scheme."""

    type_token = local_name_from_text(simple_type_name.local_name)
    scheme = MISMO_ONTOLOGY[f"{type_token}Scheme"]
    graph.add((scheme, RDF.type, SKOS.ConceptScheme))

    for value in values:
        value_digest = sha256(value.encode("utf-8")).hexdigest()[:16]
        concept = MISMO_ONTOLOGY[
            f"{type_token}-{value_digest}"
        ]
        graph.add((concept, RDF.type, SKOS.Concept))
        graph.add((concept, SKOS.prefLabel, Literal(value)))
        graph.add((concept, SKOS.inScheme, scheme))

    return scheme


def _project_simple_types(graph: Graph, model: SchemaModel) -> None:
    """Declare the named MISMO datatypes and controlled vocabularies."""

    for name, definition in sorted(
        model.simple_types.items(), key=lambda item: item[0].clark_name
    ):
        if name.namespace != MISMO_SOURCE_NAMESPACE:
            continue

        component = _schema_component_iri(model, "simpleType", name)
        _record_schema_component(graph, component, name, "simpleType")
        datatype = _ontology_term(name)

        if definition.enumeration_values:
            scheme = _project_enumeration(
                graph, name, definition.enumeration_values
            )
            graph.add((component, UAD_SCHEMA.conceptScheme, scheme))
            graph.add((component, UAD_SCHEMA.projectsTo, scheme))
            graph.add((scheme, PROV.wasDerivedFrom, component))
        else:
            graph.add((datatype, RDF.type, RDFS.Datatype))
            graph.add((component, UAD_SCHEMA.projectsTo, datatype))
            graph.add((datatype, PROV.wasDerivedFrom, component))

        graph.add(
            (
                component,
                UAD_SCHEMA.projectionDisposition,
                Literal("projected"),
            )
        )


def _property_schema_iri(
    model: SchemaModel,
    kind: str,
    name: QName,
    owner: QName | None,
) -> URIRef:
    """Mint an identity for a global declaration or local use."""

    if owner is None:
        return _schema_component_iri(model, kind, name)

    key = f"{owner.clark_name}|{kind}|{name.clark_name}"
    digest = sha256(key.encode("utf-8")).hexdigest()[:16]
    return UAD_SCHEMA[
        f"local-{kind}-{local_name_from_text(name.local_name)}-{digest}"
    ]


def _project_property(
    graph: Graph,
    model: SchemaModel,
    *,
    kind: str,
    name: QName,
    type_name: QName | None,
    owner: QName | None = None,
) -> None:
    """Project one element or attribute declaration to a property."""

    if name.namespace is None and owner is not None:
        name = QName(owner.namespace, name.local_name)

    if name.namespace != MISMO_SOURCE_NAMESPACE:
        return

    component = _property_schema_iri(model, kind, name, owner)
    _record_schema_component(graph, component, name, kind)
    property_iri = _ontology_term(name)
    range_iri, range_kind = _type_term(graph, model, type_name)

    existing_ranges = tuple(graph.objects(property_iri, RDFS.range))
    if not existing_ranges:
        property_type = (
            OWL.DatatypeProperty
            if range_kind == "datatype"
            else OWL.ObjectProperty
        )
        graph.add((property_iri, RDF.type, property_type))
        graph.add((property_iri, RDFS.range, range_iri))
    graph.add((component, UAD_SCHEMA.projectsTo, property_iri))
    graph.add((property_iri, PROV.wasDerivedFrom, component))
    graph.add(
        (
            component,
            UAD_SCHEMA.projectionDisposition,
            Literal("projected"),
        )
    )

    controlled_type = _controlled_type(model, type_name)
    if range_kind == "controlled" and controlled_type is not None:
        simple_type = model.simple_types.get(controlled_type)
        if simple_type is not None:
            scheme = _project_enumeration(
                graph, controlled_type, simple_type.enumeration_values
            )
            graph.add((property_iri, UAD_SCHEMA.conceptScheme, scheme))


def _effective_element(
    model: SchemaModel,
    declaration: ElementDeclaration,
) -> tuple[QName | None, QName | None]:
    """Resolve an element use to its effective name and type."""

    if declaration.ref is None:
        return declaration.name, declaration.type_name
    global_declaration = model.elements.get(declaration.ref)
    return (
        declaration.ref,
        None if global_declaration is None else global_declaration.type_name,
    )


def _effective_attribute(
    model: SchemaModel,
    declaration: AttributeDeclaration,
) -> tuple[QName | None, QName | None]:
    """Resolve an attribute use to its effective name and type."""

    if declaration.ref is None:
        return declaration.name, declaration.type_name
    global_declaration = model.attributes.get(declaration.ref)
    return (
        declaration.ref,
        None if global_declaration is None else global_declaration.type_name,
    )


def _project_group_particles(
    graph: Graph,
    model: SchemaModel,
    group: ModelGroup | ModelGroupReference,
    owner: QName,
    visited_groups: frozenset[QName] = frozenset(),
) -> None:
    """Project the element uses reachable through one content model."""

    if isinstance(group, ModelGroupReference):
        if group.ref in visited_groups:
            return
        referenced = model.model_groups.get(group.ref)
        if referenced is not None:
            _project_group_particles(
                graph,
                model,
                referenced,
                owner,
                visited_groups | {group.ref},
            )
        return

    for particle in group.particles:
        if isinstance(particle, ElementDeclaration):
            name, type_name = _effective_element(model, particle)
            if name is not None:
                _project_property(
                    graph,
                    model,
                    kind="element",
                    name=name,
                    type_name=type_name,
                    owner=owner,
                )
        elif isinstance(particle, (ModelGroup, ModelGroupReference)):
            _project_group_particles(
                graph,
                model,
                particle,
                owner,
                visited_groups,
            )


def _project_attribute_group(
    graph: Graph,
    model: SchemaModel,
    group_name: QName,
    owner: QName,
    visited_groups: frozenset[QName] = frozenset(),
) -> None:
    """Project attributes reachable through an attribute-group use."""

    if group_name in visited_groups:
        return
    group = model.attribute_groups.get(group_name)
    if group is None:
        return

    visited = visited_groups | {group_name}
    for declaration in group.attributes:
        name, type_name = _effective_attribute(model, declaration)
        if name is not None:
            _project_property(
                graph,
                model,
                kind="attribute",
                name=name,
                type_name=type_name,
                owner=owner,
            )
    for referenced_group in group.referenced_groups:
        _project_attribute_group(
            graph, model, referenced_group, owner, visited
        )


def _project_declarations(graph: Graph, model: SchemaModel) -> None:
    """Project global declarations and all represented local uses."""

    for name, declaration in sorted(
        model.elements.items(), key=lambda item: item[0].clark_name
    ):
        _project_property(
            graph,
            model,
            kind="element",
            name=name,
            type_name=declaration.type_name,
        )

    for name, declaration in sorted(
        model.attributes.items(), key=lambda item: item[0].clark_name
    ):
        _project_property(
            graph,
            model,
            kind="attribute",
            name=name,
            type_name=declaration.type_name,
        )

    for owner, complex_type in sorted(
        model.complex_types.items(), key=lambda item: item[0].clark_name
    ):
        if complex_type.content is not None:
            _project_group_particles(
                graph, model, complex_type.content, owner
            )
        for declaration in complex_type.attributes:
            name, type_name = _effective_attribute(model, declaration)
            if name is not None:
                _project_property(
                    graph,
                    model,
                    kind="attribute",
                    name=name,
                    type_name=type_name,
                    owner=owner,
                )
        for group_name in complex_type.attribute_group_refs:
            _project_attribute_group(
                graph, model, group_name, owner
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
    source_identities: dict[Path, tuple[URIRef, str]] = {}
    _record_occurrence_dispositions(
        graph,
        model,
        source_identities,
    )

    for complex_type in model.complex_types.values():
        component_iri = _schema_component_iri(
            model,
            "complexType",
            complex_type.name,
        )
        _record_schema_component(
            graph,
            component_iri,
            complex_type.name,
            "complexType",
        )
        if complex_type.source_document is not None:
            _record_source_document_traceability(
                graph,
                component_iri,
                complex_type.source_document,
                source_identities,
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

    _project_simple_types(graph, model)
    _project_declarations(graph, model)

    unresolved_global_kinds = (
        ("simpleType", model.simple_types),
        ("element", model.elements),
        ("attribute", model.attributes),
        ("attributeGroup", model.attribute_groups),
        ("group", model.model_groups),
    )
    for component_kind, components in unresolved_global_kinds:
        for qname in components:
            component_iri = _schema_component_iri(
                model,
                component_kind,
                qname,
            )
            _record_schema_component(
                graph,
                component_iri,
                qname,
                component_kind,
            )
            if any(
                graph.objects(
                    component_iri,
                    UAD_SCHEMA.projectionDisposition,
                )
            ):
                continue
            graph.add(
                (
                    component_iri,
                    UAD_SCHEMA.projectionDisposition,
                    Literal("unresolved"),
                )
            )

    return graph


def serialize_logical_schema_ontology(
    model: SchemaModel,
    output_file: Path,
) -> Path:
    """Project a Logical Schema Model and serialize it as Turtle."""

    graph = project_logical_schema_to_ontology(model)

    output_file.parent.mkdir(parents=True, exist_ok=True)
    graph.serialize(
        destination=str(output_file),
        format="turtle",
        encoding="utf-8",
    )

    return output_file


__all__ = [
    "MINTING_POLICY_VERSION",
    "MISMO_ONTOLOGY",
    "MISMO_SOURCE_NAMESPACE",
    "PROV",
    "RECONCILIATION_IRI",
    "UAD_SCHEMA",
    "project_logical_schema_to_ontology",
    "serialize_logical_schema_ontology",
]
