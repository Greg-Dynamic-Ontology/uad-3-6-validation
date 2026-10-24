"""Bind classified governed constraints to the established RDF projection."""

from __future__ import annotations

from hashlib import sha256
from itertools import product
import json

from rdflib import Graph, Literal, Namespace, RDF, RDFS, URIRef
from rdflib.collection import Collection
from rdflib.namespace import OWL, PROV

from app.services.construction_exchange import (
    UADEX,
    ConstructionStageResultRecord,
    exchange_successful_construction_stage_result,
    exchange_construction_stage_exception,
)
from app.services.rdf_projection import UAD_SCHEMA


CV = Namespace("https://dynamicontology.com/uad36/constraint-vocabulary#")
LSM = Namespace("https://dynamicontology.com/uad36/logical-schema#")


class _UnresolvedProjection(ValueError):
    """A governed schema resource has no declared projection predicate."""

    def __init__(self, schema_resource: URIRef, expanded_name: Literal) -> None:
        self.schema_resource = schema_resource
        super().__init__(
            f"Schema resource {schema_resource} (QName {expanded_name}) has no "
            "established Instance RDF predicate in the projection model."
        )

def _one(graph: Graph, subject, predicate):
    values = set(graph.objects(subject, predicate))
    if len(values) != 1:
        raise ValueError(f"{subject} must identify exactly one {predicate}.")
    return next(iter(values))


def _expanded_name(qname: URIRef, model: Graph, classified: Graph) -> Literal:
    """Read explicit QName knowledge rather than parsing an opaque schema IRI."""
    source_names = set(model.objects(qname, UAD_SCHEMA.sourceQName))
    source_names.update(classified.objects(qname, UAD_SCHEMA.sourceQName))
    if source_names:
        if len(source_names) != 1:
            raise ValueError(f"Schema resource {qname} has ambiguous source QNames.")
        value = next(iter(source_names))
        if not isinstance(value, Literal) or not str(value).strip():
            raise ValueError("Source QName must be a nonblank RDF literal.")
        return value

    local_names = set(model.objects(qname, LSM.local_name))
    local_names.update(classified.objects(qname, LSM.local_name))
    namespaces = set(model.objects(qname, LSM.namespace))
    namespaces.update(classified.objects(qname, LSM.namespace))
    if len(local_names) != 1 or len(namespaces) > 1:
        raise ValueError(f"Schema resource {qname} lacks one governed QName.")
    local_name = next(iter(local_names))
    namespace = next(iter(namespaces), None)
    if not isinstance(local_name, Literal) or not str(local_name).strip():
        raise ValueError("QName local name must be a nonblank RDF literal.")
    return Literal(
        f"{{{namespace}}}{local_name}" if namespace is not None else str(local_name)
    )


def _projected_properties(qname: URIRef, model: Graph, classified: Graph) -> tuple[URIRef, ...]:
    expanded_name = _expanded_name(qname, model, classified)
    properties = {
        term
        for component in model.subjects(UAD_SCHEMA.sourceQName, expanded_name)
        for term in model.objects(component, UAD_SCHEMA.projectsTo)
        if isinstance(term, URIRef)
        and any(
            (term, RDF.type, property_type) in model
            for property_type in (RDF.Property, OWL.ObjectProperty, OWL.DatatypeProperty)
        )
    }
    if not properties:
        raise _UnresolvedProjection(qname, expanded_name)
    return tuple(sorted(properties, key=str))


def _resource_class(model: Graph, predicate: URIRef) -> URIRef:
    value = _one(model, predicate, RDFS.range)
    if not isinstance(value, URIRef) or not any(
        (value, RDF.type, class_type) in model
        for class_type in (OWL.Class, RDFS.Class)
    ):
        raise ValueError(f"{predicate} must project to a declared resource class.")
    return value


def bind_governed_constraint_to_instance_rdf(
    *,
    classified_graph: Graph,
    projection_model_graph: Graph,
    constraint_id: str,
    output_graph: Graph,
) -> ConstructionStageResultRecord:
    """Produce a reusable model binding without consuming an appraisal report."""
    if output_graph is classified_graph or output_graph is projection_model_graph:
        raise ValueError("output_graph must be separate from the input graphs.")
    if not constraint_id.strip():
        raise ValueError("constraint_id is required.")
    constraint = URIRef(constraint_id)
    if (constraint, RDF.type, CV.NormalizedConstraint) not in classified_graph:
        raise ValueError("constraint_id must identify a NormalizedConstraint.")

    schema_resource = _one(classified_graph, constraint, CV.boundLogicalSchemaResource)
    context = _one(classified_graph, constraint, CV.applicableContext)
    classification = _one(classified_graph, constraint, CV.behaviorClassification)
    for resource in (schema_resource, context, classification):
        if not isinstance(resource, URIRef):
            raise ValueError("Governed bindings and context must retain their IRIs.")
    if (context, RDF.type, CV.ConstraintContext) not in classified_graph:
        raise ValueError("The applicable context must identify a ConstraintContext.")
    if (classification, RDF.type, CV.ValidationBehaviorClassification) not in classified_graph:
        raise ValueError("The constraint must have a governed behavior classification.")
    behavior = _one(classified_graph, classification, CV.validationBehavior)
    if not isinstance(behavior, URIRef):
        raise ValueError("Validation behavior must retain its governed IRI.")
    if _one(classified_graph, classification, CV.applicableContext) != context:
        raise ValueError("Behavior classification must preserve the applicable context.")
    sources = set(classified_graph.objects(constraint, PROV.wasDerivedFrom))
    if not sources:
        raise ValueError("The constraint must preserve governed source provenance.")

    path_head = _one(classified_graph, context, CV.schemaPath)
    schema_path = list(Collection(classified_graph, path_head))
    if len(schema_path) < 2 or any(not isinstance(item, URIRef) for item in schema_path):
        raise ValueError("The context must supply an ordered governed element path.")
    if schema_path[-1] != schema_resource:
        # IT-52 preserves an ElementDeclaration identity, while IT-53 records
        # its governed QName in the ordered context path. Verify the explicit
        # schema relationship without replacing either governed identity.
        schema_names = set()
        declaration_is_known = False
        for knowledge in (classified_graph, projection_model_graph):
            declaration_is_known = declaration_is_known or (
                schema_resource, RDF.type, LSM.ElementDeclaration
            ) in knowledge
            schema_names.update(knowledge.objects(schema_resource, LSM.name))
            schema_names.update(knowledge.objects(schema_resource, LSM.ref))
        if not declaration_is_known or schema_names != {schema_path[-1]}:
            raise ValueError(
                "The bound schema resource must terminate the governed path "
                "or explicitly declare its terminal governed QName."
            )

    try:
        projection_options = [
            _projected_properties(resource, projection_model_graph, classified_graph)
            for resource in schema_path
        ]
    except _UnresolvedProjection as error:
        # Preserve the input knowledge without manufacturing a successful
        # binding, class, predicate, or path for the unresolved resource.
        for graph in (classified_graph, projection_model_graph):
            for prefix, namespace in graph.namespaces():
                output_graph.bind(prefix, namespace, replace=False)
            for triple in graph:
                output_graph.add(triple)
        result = exchange_construction_stage_exception(
            exchange_graph=output_graph,
            constraint_id=str(constraint),
            construction_stage="instance-rdf-binding",
            exception_reason=str(error),
            requires_review=True,
        )
        for triple in (
            (result.result_id, CV.unresolvedLogicalSchemaResource, error.schema_resource),
            (result.result_id, CV.applicableContext, context),
            (result.result_id, CV.behaviorClassification, classification),
        ):
            output_graph.add(triple)
        for source in sources:
            output_graph.add((result.result_id, PROV.wasDerivedFrom, source))
        return result
    # Enumerate complete model-supported paths. Never select a predicate by
    # insertion order or lexical order when more than one binding is possible.
    projected_candidates = list(product(*projection_options))
    candidate_bindings = set()
    for properties in projected_candidates:
        candidate_focus = _resource_class(projection_model_graph, properties[0])
        for predicate in properties[1:-1]:
            _resource_class(projection_model_graph, predicate)
        candidate_bindings.add((candidate_focus, tuple(properties[1:])))

    if len(candidate_bindings) > 1:
        for graph in (classified_graph, projection_model_graph):
            for prefix, namespace in graph.namespaces():
                output_graph.bind(prefix, namespace, replace=False)
            for triple in graph:
                output_graph.add(triple)
        result = exchange_construction_stage_exception(
            exchange_graph=output_graph,
            constraint_id=str(constraint),
            construction_stage="instance-rdf-binding",
            exception_reason=(
                f"The governed context permits {len(candidate_bindings)} "
                "incompatible Instance RDF bindings in the established "
                "projection model. No binding was selected; review is required."
            ),
            requires_review=True,
        )
        output_graph.add((result.result_id, CV.applicableContext, context))
        output_graph.add((result.result_id, CV.behaviorClassification, classification))
        for source in sources:
            output_graph.add((result.result_id, PROV.wasDerivedFrom, source))
        for candidate_focus, candidate_path in sorted(
            candidate_bindings,
            key=lambda item: (str(item[0]), tuple(map(str, item[1]))),
        ):
            identity = json.dumps(
                [str(context), str(classification), str(candidate_focus),
                 *map(str, candidate_path)],
                separators=(",", ":"),
            )
            digest = sha256(identity.encode("utf-8")).hexdigest()
            candidate = URIRef(f"{constraint}/candidate-instance-rdf-binding/{digest}")
            path_node = URIRef(f"{candidate}/predicate-path")
            for triple in (
                (result.result_id, CV.candidateInstanceRdfBinding, candidate),
                (candidate, RDF.type, CV.CandidateInstanceRdfBinding),
                (candidate, CV.focusClass, candidate_focus),
                (candidate, CV.predicatePath, path_node),
                (candidate, CV.valuePredicate, candidate_path[-1]),
                (candidate, CV.applicableContext, context),
                (candidate, CV.boundLogicalSchemaResource, schema_resource),
                (candidate, CV.behaviorClassification, classification),
                (candidate, CV.validationBehavior, behavior),
            ):
                output_graph.add(triple)
            Collection(output_graph, path_node, list(candidate_path))
            for source in sources:
                output_graph.add((candidate, PROV.wasDerivedFrom, source))
        return result

    projected_properties = projected_candidates[0]
    focus_class = _resource_class(projection_model_graph, projected_properties[0])
    for predicate in projected_properties[1:-1]:
        _resource_class(projection_model_graph, predicate)
    predicate_path = projected_properties[1:]

    identity = json.dumps(
        [str(context), str(classification), str(focus_class), *map(str, predicate_path)],
        separators=(",", ":"),
    )
    digest = sha256(identity.encode("utf-8")).hexdigest()
    binding = URIRef(f"{constraint}/instance-rdf-binding/{digest}")

    for graph in (classified_graph, projection_model_graph):
        for prefix, namespace in graph.namespaces():
            output_graph.bind(prefix, namespace, replace=False)
        for triple in graph:
            output_graph.add(triple)
    for triple in (
        (constraint, CV.instanceRdfBinding, binding),
        (binding, RDF.type, CV.InstanceRdfBinding),
        (binding, CV.boundLogicalSchemaResource, schema_resource),
        (binding, CV.applicableContext, context),
        (binding, CV.behaviorClassification, classification),
        (binding, CV.validationBehavior, behavior),
        (binding, CV.focusClass, focus_class),
        (binding, CV.valuePredicate, predicate_path[-1]),
        (binding, CV.predicatePath, URIRef(f"{binding}/predicate-path")),
    ):
        output_graph.add(triple)
    Collection(output_graph, URIRef(f"{binding}/predicate-path"), predicate_path)
    for source in sources:
        output_graph.add((binding, PROV.wasDerivedFrom, source))

    result = exchange_successful_construction_stage_result(
        exchange_graph=output_graph,
        constraint_id=str(constraint),
        construction_stage="instance-rdf-binding",
    )
    output_graph.add((result.result_id, UADEX.stageKnowledge, binding))
    return result


__all__ = ["bind_governed_constraint_to_instance_rdf"]
