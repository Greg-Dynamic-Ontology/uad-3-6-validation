"""Resolve governed applicable context for bound normalized constraints."""

from __future__ import annotations

from hashlib import sha256
import json
import re

from rdflib import Graph, Literal, Namespace, RDF, URIRef
from rdflib.collection import Collection
from rdflib.namespace import PROV

from app.services.construction_exchange import (
    UADEX,
    ConstructionStageResultRecord,
    exchange_construction_stage_exception,
    exchange_successful_construction_stage_result,
)
from app.services.logical_schema_serializer import (
    LOGICAL_SCHEMA_MODEL_IRI,
)


CV = Namespace(
    "https://dynamicontology.com/uad36/constraint-vocabulary#"
)
LSM = Namespace(
    "https://dynamicontology.com/uad36/logical-schema#"
)

_ELEMENT_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_.-]*")


class _UnresolvedContext(ValueError):
    """Valid source context has no matching governed schema path."""


class _AmbiguousContext(ValueError):
    """Source context permits multiple governed schema paths."""

    def __init__(
        self,
        candidate_paths: tuple[tuple[URIRef, ...], ...],
    ) -> None:
        self.candidate_paths = tuple(
            sorted(
                candidate_paths,
                key=lambda path: tuple(str(resource) for resource in path),
            )
        )
        super().__init__(
            "Governed source context permits multiple schema paths "
            "ending at the bound Logical Schema resource; "
            f"found {len(self.candidate_paths)}. Review is required."
        )


def _copy_knowledge(source: Graph, destination: Graph) -> None:
    for prefix, namespace in source.namespaces():
        destination.bind(prefix, namespace, replace=False)
    for triple in source:
        destination.add(triple)


def _members(graph: Graph, container) -> set:
    """Read the serializer's collection or mapping representation."""
    values = set(graph.objects(container, LSM.member))
    for entry in graph.objects(container, LSM.entry):
        values.update(graph.objects(entry, LSM.value))
    return values


def _model_values(graph: Graph, predicate) -> set:
    values = set()
    for container in graph.objects(
        LOGICAL_SCHEMA_MODEL_IRI,
        predicate,
    ):
        values.update(_members(graph, container))
    return values


def _index_by_name(graph: Graph, resources: set) -> dict:
    index = {}
    for resource in resources:
        for name in graph.objects(resource, LSM.name):
            index.setdefault(name, set()).add(resource)
    return index


def _element_qname(graph: Graph, declaration) -> URIRef:
    names = set(graph.objects(declaration, LSM.name))
    names.update(graph.objects(declaration, LSM.ref))

    if len(names) != 1:
        raise ValueError(
            "A schema path element must identify exactly one QName."
        )

    name = next(iter(names))
    if not isinstance(name, URIRef):
        raise ValueError(
            "A schema path must preserve a governed QName IRI."
        )
    return name


def _local_name(graph: Graph, qname: URIRef) -> str:
    names = set(graph.objects(qname, LSM.local_name))
    if len(names) != 1:
        raise ValueError(
            f"QName {qname} must identify exactly one local name."
        )
    return str(next(iter(names)))


def _children(
    graph: Graph,
    declaration,
    element_index: dict,
    type_index: dict,
    group_index: dict,
) -> set:
    """Find immediate element children through schema content models."""
    definitions = [declaration]
    visited_definitions = set()
    pending = []

    while definitions:
        definition = definitions.pop()
        if definition in visited_definitions:
            continue
        visited_definitions.add(definition)

        for type_name in graph.objects(definition, LSM.type_name):
            pending.extend(type_index.get(type_name, ()))

        for reference in graph.objects(definition, LSM.ref):
            definitions.extend(element_index.get(reference, ()))

        pending.extend(graph.objects(definition, LSM.content))

    children = set()
    visited = set()

    while pending:
        resource = pending.pop()
        if resource in visited:
            continue
        visited.add(resource)

        if (
            resource,
            RDF.type,
            LSM.ElementDeclaration,
        ) in graph:
            children.add(resource)
            continue

        pending.extend(graph.objects(resource, LSM.content))

        for predicate in (
            LSM.particles,
            LSM.elements,
            LSM.groups,
        ):
            for container in graph.objects(resource, predicate):
                pending.extend(_members(graph, container))

        for base_type in graph.objects(resource, LSM.base_type):
            pending.extend(type_index.get(base_type, ()))

        for reference in graph.objects(resource, LSM.ref):
            pending.extend(group_index.get(reference, ()))

    return children


def _source_path(
    bound_graph: Graph,
    source_context_nodes: set,
) -> tuple[str, ...]:
    paths = set()

    for node in source_context_nodes:
        values = set(bound_graph.objects(node, CV.contextValue))
        if len(values) != 1:
            raise ValueError(
                "Each source-context resource must have one contextValue."
            )

        value = next(iter(values))
        if not isinstance(value, Literal):
            raise ValueError("Source context values must be RDF literals.")

        text = str(value).strip()
        if not text.startswith("/"):
            continue

        tokens = text[1:].split("/")
        if not tokens or any(
            _ELEMENT_NAME.fullmatch(token) is None
            for token in tokens
        ):
            raise ValueError(
                "Context resolution currently requires an explicit "
                "absolute element path without XPath expressions."
            )

        paths.add(tuple(tokens))

    if len(paths) != 1:
        raise ValueError(
            "Source knowledge must identify exactly one explicit "
            "absolute context path."
        )

    return next(iter(paths))


def _resolve_schema_path(
    graph: Graph,
    source_path: tuple[str, ...],
    bound_resource: URIRef,
) -> tuple[URIRef, ...]:
    roots = _model_values(graph, LSM.elements)
    element_index = _index_by_name(graph, roots)
    type_index = _index_by_name(
        graph,
        _model_values(graph, LSM.complex_types),
    )
    group_index = _index_by_name(
        graph,
        _model_values(graph, LSM.model_groups),
    )

    def matches(declaration, expected_name: str) -> bool:
        qname = _element_qname(graph, declaration)
        return _local_name(graph, qname) == expected_name

    candidates = {
        (root,)
        for root in roots
        if (
            root,
            RDF.type,
            LSM.ElementDeclaration,
        ) in graph
        and matches(root, source_path[0])
    }

    for name in source_path[1:]:
        candidates = {
            path + (child,)
            for path in candidates
            for child in _children(
                graph,
                path[-1],
                element_index,
                type_index,
                group_index,
            )
            if matches(child, name)
        }

    candidates = {
        path
        for path in candidates
        if path[-1] == bound_resource
    }

    if not candidates:
        raise _UnresolvedContext(
            "No governed schema path is consistent with the "
            "source context and bound Logical Schema resource."
        )

    candidate_paths = tuple(
        tuple(
            _element_qname(graph, declaration)
            for declaration in path
        )
        for path in candidates
    )

    if len(candidate_paths) != 1:
        raise _AmbiguousContext(candidate_paths)

    return candidate_paths[0]


def _record_context_exception(
    *,
    bound_graph: Graph,
    output_graph: Graph,
    constraint: URIRef,
    source_context_nodes: set,
    source_constraints: set,
    reason: str,
) -> ConstructionStageResultRecord:
    """Preserve unsuccessful resolution as governed exchange knowledge."""
    context_values = sorted(
        str(value)
        for node in source_context_nodes
        for value in bound_graph.objects(node, CV.contextValue)
    )
    exception_reason = (
        f"{reason} Source context values: "
        f"{json.dumps(context_values, ensure_ascii=True)}"
    )

    _copy_knowledge(bound_graph, output_graph)

    result = exchange_construction_stage_exception(
        exchange_graph=output_graph,
        constraint_id=str(constraint),
        construction_stage="context-resolution",
        exception_reason=exception_reason,
        requires_review=True,
    )

    for source_context in source_context_nodes:
        output_graph.add(
            (
                result.result_id,
                CV.hasSourceContext,
                source_context,
            )
        )

    for source_constraint in source_constraints:
        output_graph.add(
            (
                result.result_id,
                PROV.wasDerivedFrom,
                source_constraint,
            )
        )
    output_graph.add(
        (
            result.result_id,
            PROV.wasDerivedFrom,
            LOGICAL_SCHEMA_MODEL_IRI,
        )
    )

    return result


def _record_candidates(
    *,
    output_graph: Graph,
    result_id: URIRef,
    candidate_paths: tuple[tuple[URIRef, ...], ...],
    source_context_nodes: set,
) -> None:
    """Record all candidates without selecting an applicable context."""
    for index, schema_path in enumerate(candidate_paths, start=1):
        candidate = URIRef(
            f"{result_id}/candidate-context/{index}"
        )
        path_head = URIRef(f"{candidate}/schema-path")

        output_graph.add(
            (result_id, CV.candidateContext, candidate)
        )
        Collection(output_graph, path_head, list(schema_path))
        output_graph.add(
            (candidate, CV.schemaPath, path_head)
        )
        output_graph.add(
            (
                candidate,
                PROV.wasDerivedFrom,
                LOGICAL_SCHEMA_MODEL_IRI,
            )
        )

        for source_context in source_context_nodes:
            output_graph.add(
                (candidate, CV.hasSourceContext, source_context)
            )


def resolve_bound_constraint_context(
    *,
    bound_graph: Graph,
    logical_schema_graph: Graph,
    constraint_id: str,
    output_graph: Graph,
) -> ConstructionStageResultRecord:
    """Produce one governed context or a reviewable context exception."""
    if output_graph is bound_graph or output_graph is logical_schema_graph:
        raise ValueError(
            "output_graph must be separate from the input graphs."
        )

    if not constraint_id.strip():
        raise ValueError("constraint_id is required.")

    constraint = URIRef(constraint_id)
    if (
        constraint,
        RDF.type,
        CV.NormalizedConstraint,
    ) not in bound_graph:
        raise ValueError(
            "constraint_id must identify a NormalizedConstraint "
            "in bound_graph."
        )

    if (
        LOGICAL_SCHEMA_MODEL_IRI,
        RDF.type,
        LSM.SchemaModel,
    ) not in logical_schema_graph:
        raise ValueError(
            "The governed Logical Schema Model must be present."
        )

    bindings = set(
        bound_graph.objects(
            constraint,
            CV.boundLogicalSchemaResource,
        )
    )
    if len(bindings) != 1:
        raise ValueError(
            "The constraint must have exactly one Logical Schema binding."
        )

    bound_resource = next(iter(bindings))
    if not isinstance(bound_resource, URIRef):
        raise ValueError(
            "The Logical Schema binding must identify a governed IRI."
        )

    source_context_nodes = set(
        bound_graph.objects(constraint, CV.hasSourceContext)
    )
    if not source_context_nodes:
        raise ValueError("Governed source context is required.")

    source_constraints = set(
        bound_graph.objects(constraint, PROV.wasDerivedFrom)
    )
    if not source_constraints:
        raise ValueError(
            "The normalized constraint must retain source provenance."
        )

    source_path = _source_path(
        bound_graph,
        source_context_nodes,
    )

    try:
        schema_path = _resolve_schema_path(
            logical_schema_graph,
            source_path,
            bound_resource,
        )
    except _UnresolvedContext as error:
        return _record_context_exception(
            bound_graph=bound_graph,
            output_graph=output_graph,
            constraint=constraint,
            source_context_nodes=source_context_nodes,
            source_constraints=source_constraints,
            reason=str(error),
        )
    except _AmbiguousContext as error:
        result = _record_context_exception(
            bound_graph=bound_graph,
            output_graph=output_graph,
            constraint=constraint,
            source_context_nodes=source_context_nodes,
            source_constraints=source_constraints,
            reason=str(error),
        )
        _record_candidates(
            output_graph=output_graph,
            result_id=result.result_id,
            candidate_paths=error.candidate_paths,
            source_context_nodes=source_context_nodes,
        )
        return result

    identity = json.dumps(
        [str(resource) for resource in schema_path],
        ensure_ascii=True,
        separators=(",", ":"),
    )
    digest = sha256(identity.encode("utf-8")).hexdigest()
    context = URIRef(f"{constraint}/context/{digest}")

    _copy_knowledge(bound_graph, output_graph)

    output_graph.add(
        (constraint, CV.applicableContext, context)
    )
    output_graph.add(
        (context, RDF.type, CV.ConstraintContext)
    )

    path_head = URIRef(f"{context}/schema-path")
    Collection(output_graph, path_head, list(schema_path))
    output_graph.add(
        (context, CV.schemaPath, path_head)
    )

    for source_context in source_context_nodes:
        output_graph.add(
            (context, CV.hasSourceContext, source_context)
        )

    for source_constraint in source_constraints:
        output_graph.add(
            (context, PROV.wasDerivedFrom, source_constraint)
        )
    output_graph.add(
        (
            context,
            PROV.wasDerivedFrom,
            LOGICAL_SCHEMA_MODEL_IRI,
        )
    )

    result = exchange_successful_construction_stage_result(
        exchange_graph=output_graph,
        constraint_id=str(constraint),
        construction_stage="context-resolution",
    )
    output_graph.add(
        (result.result_id, UADEX.stageKnowledge, context)
    )
    return result


__all__ = ["resolve_bound_constraint_context"]