"""Derive executable SHACL from governed behavior and Instance RDF bindings."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

from rdflib import BNode, Graph, Literal, Namespace, RDF, URIRef
from rdflib.collection import Collection
from rdflib.namespace import PROV, SH

from app.services.construction_exchange import (
    UADEX,
    ConstructionStageResultRecord,
    exchange_successful_construction_stage_result,
    exchange_construction_stage_exception,
)


CV = Namespace("https://dynamicontology.com/uad36/constraint-vocabulary#")

# Scalar property-shape components can be copied without rewriting their
# meaning. Structured patterns require a separately governed implementation.
_SCALAR_COMPONENTS = {
    SH[name]
    for name in (
        "minCount", "maxCount", "minLength", "maxLength", "datatype",
        "nodeKind", "class", "pattern", "flags", "minInclusive",
        "maxInclusive", "minExclusive", "maxExclusive", "severity",
    )
}


def _one(graph: Graph, subject, predicate):
    values = set(graph.objects(subject, predicate))
    if len(values) != 1:
        raise ValueError(f"{subject} must identify exactly one {predicate}.")
    return next(iter(values))


def _copy(source: Graph, destination: Graph) -> None:
    for prefix, namespace in source.namespaces():
        destination.bind(prefix, namespace, replace=False)
    for triple in source:
        destination.add(triple)


def generate_governed_constraint_shacl(
    *,
    bound_graph: Graph,
    implementation_patterns_graph: Graph,
    constraint_id: str,
    output_path: Path | str,
    output_graph: Graph,
) -> ConstructionStageResultRecord:
    """Persist one SHACL representation and publish its construction result.

    The caller supplies the governed artifact destination. This worker does
    not read an appraisal instance, execute validation, or generate findings.
    """
    if output_graph is bound_graph or output_graph is implementation_patterns_graph:
        raise ValueError("output_graph must be separate from the input graphs.")
    if not constraint_id.strip():
        raise ValueError("constraint_id is required.")
    constraint = URIRef(constraint_id)
    if (constraint, RDF.type, CV.NormalizedConstraint) not in bound_graph:
        raise ValueError("constraint_id must identify a NormalizedConstraint.")

    requirement = _one(bound_graph, constraint, CV.requirementText)
    violation = _one(bound_graph, constraint, CV.violationCondition)
    for value in (requirement, violation):
        if not isinstance(value, Literal) or not str(value).strip():
            raise ValueError("Governed requirement and violation must be nonblank literals.")
    schema_resource = _one(bound_graph, constraint, CV.boundLogicalSchemaResource)
    context = _one(bound_graph, constraint, CV.applicableContext)
    classification = _one(bound_graph, constraint, CV.behaviorClassification)
    binding = _one(bound_graph, constraint, CV.instanceRdfBinding)
    for resource in (schema_resource, context, classification, binding):
        if not isinstance(resource, URIRef):
            raise ValueError("Governed identities must be IRIs.")
    for resource, expected_type in (
        (context, CV.ConstraintContext),
        (classification, CV.ValidationBehaviorClassification),
        (binding, CV.InstanceRdfBinding),
    ):
        if (resource, RDF.type, expected_type) not in bound_graph:
            raise ValueError(f"{resource} must identify a {expected_type}.")
    behavior = _one(bound_graph, classification, CV.validationBehavior)
    if not isinstance(behavior, URIRef):
        raise ValueError("Validation behavior must preserve its governed IRI.")
    for resource, predicate, expected in (
        (classification, CV.applicableContext, context),
        (binding, CV.boundLogicalSchemaResource, schema_resource),
        (binding, CV.applicableContext, context),
        (binding, CV.behaviorClassification, classification),
        (binding, CV.validationBehavior, behavior),
    ):
        if _one(bound_graph, resource, predicate) != expected:
            raise ValueError("Governed classification, context, and binding must agree.")
    sources = set(bound_graph.objects(constraint, PROV.wasDerivedFrom))
    if not sources:
        raise ValueError("Governed source provenance is required.")

    focus_class = _one(bound_graph, binding, CV.focusClass)
    path_head = _one(bound_graph, binding, CV.predicatePath)
    predicates = list(Collection(bound_graph, path_head))
    if not isinstance(focus_class, URIRef) or not predicates or any(
        not isinstance(predicate, URIRef) for predicate in predicates
    ):
        raise ValueError("The Instance RDF binding must supply a class and predicate path.")
    if _one(bound_graph, binding, CV.valuePredicate) != predicates[-1]:
        raise ValueError("The value predicate must terminate the Instance RDF path.")

    established_patterns = set(
        implementation_patterns_graph.objects(behavior, CV.shaclImplementationPattern)
    )
    if not established_patterns:
        # A missing implementation is governed construction knowledge. Do not
        # create a directory, write an artifact, or infer a default pattern.
        _copy(bound_graph, output_graph)
        result = exchange_construction_stage_exception(
            exchange_graph=output_graph,
            constraint_id=str(constraint),
            construction_stage="shacl-representation",
            exception_reason=(
                f"Validation behavior {behavior} has no governed SHACL "
                "implementation pattern. No SHACL representation was generated; "
                "governance review is required."
            ),
            requires_review=True,
        )
        for triple in (
            (result.result_id, CV.validationBehavior, behavior),
            (result.result_id, CV.applicableContext, context),
            (result.result_id, CV.instanceRdfBinding, binding),
        ):
            output_graph.add(triple)
        for source in sources:
            output_graph.add((result.result_id, PROV.wasDerivedFrom, source))
        return result

    alternatives = set()
    for candidate_pattern in established_patterns:
        if (
            candidate_pattern, RDF.type, CV.ShaclImplementationPattern
        ) not in implementation_patterns_graph:
            raise ValueError("The behavior must identify a governed SHACL implementation pattern.")
        templates = set(
            implementation_patterns_graph.objects(candidate_pattern, CV.propertyShapeTemplate)
        )
        if not templates:
            raise ValueError("The implementation pattern must identify a property-shape template.")
        for candidate_template in templates:
            if (
                candidate_template, RDF.type, SH.PropertyShape
            ) not in implementation_patterns_graph:
                raise ValueError("The implementation pattern must identify a property-shape template.")
            alternatives.add((candidate_pattern, candidate_template))

    if len(alternatives) > 1:
        # Record alternatives as review knowledge. No alternative becomes an
        # executable shape, and no output directory or artifact is created.
        _copy(bound_graph, output_graph)
        result = exchange_construction_stage_exception(
            exchange_graph=output_graph,
            constraint_id=str(constraint),
            construction_stage="shacl-representation",
            exception_reason=(
                f"Validation behavior {behavior} permits {len(alternatives)} "
                "SHACL implementation alternatives. No representation was "
                "selected or generated; governance review is required."
            ),
            requires_review=True,
        )
        for triple in (
            (result.result_id, CV.validationBehavior, behavior),
            (result.result_id, CV.applicableContext, context),
            (result.result_id, CV.instanceRdfBinding, binding),
        ):
            output_graph.add(triple)
        for source in sources:
            output_graph.add((result.result_id, PROV.wasDerivedFrom, source))
        for candidate_pattern, candidate_template in sorted(
            alternatives, key=lambda pair: tuple(map(str, pair))
        ):
            identity = json.dumps(
                [str(constraint), str(binding), str(candidate_pattern), str(candidate_template)],
                separators=(",", ":"),
            )
            digest = sha256(identity.encode("utf-8")).hexdigest()
            candidate = URIRef(f"{constraint}/candidate-shacl/{digest}")
            for triple in (
                (result.result_id, CV.candidateShaclRepresentation, candidate),
                (candidate, RDF.type, CV.CandidateShaclRepresentation),
                (candidate, CV.shaclImplementationPattern, candidate_pattern),
                (candidate, CV.propertyShapeTemplate, candidate_template),
                (candidate, CV.instanceRdfBinding, binding),
                (candidate, CV.applicableContext, context),
            ):
                output_graph.add(triple)
            # Preserve the actual source definitions so reviewers can inspect
            # what differs. These are templates, not generated executable shapes.
            for resource in (candidate_pattern, candidate_template):
                for triple in implementation_patterns_graph.triples((resource, None, None)):
                    output_graph.add(triple)
            for source in sources:
                output_graph.add((candidate, PROV.wasDerivedFrom, source))
        return result

    pattern, template = next(iter(alternatives))
    components = []
    for predicate, value in implementation_patterns_graph.predicate_objects(template):
        if predicate == RDF.type:
            continue
        if str(predicate).startswith(str(SH)):
            if predicate not in _SCALAR_COMPONENTS or not isinstance(value, (Literal, URIRef)):
                raise ValueError(f"Unsupported governed property-shape component: {predicate}.")
            components.append((predicate, value))
    if not components or not any(predicate != SH.severity for predicate, _ in components):
        raise ValueError("The established pattern must supply an executable constraint component.")

    identity = json.dumps(
        [str(constraint), str(binding), str(pattern)], separators=(",", ":")
    )
    digest = sha256(identity.encode("utf-8")).hexdigest()
    shape = URIRef(f"{constraint}/shacl/{digest}")
    property_shape = URIRef(f"{shape}/property")
    shapes = Graph()
    shapes.bind("sh", SH)
    shapes.bind("cv", CV)
    shapes.bind("prov", PROV)
    for triple in (
        (constraint, CV.shaclRepresentation, shape),
        (shape, RDF.type, SH.NodeShape),
        (shape, CV.implementsConstraint, constraint),
        (shape, PROV.wasDerivedFrom, pattern),
        (shape, PROV.wasDerivedFrom, binding),
        (shape, SH.targetClass, focus_class),
        (shape, SH.property, property_shape),
        (property_shape, RDF.type, SH.PropertyShape),
        (property_shape, SH.message, requirement),
    ):
        shapes.add(triple)
    for source in sources:
        shapes.add((shape, PROV.wasDerivedFrom, source))
    for predicate, value in components:
        shapes.add((property_shape, predicate, value))
    if len(predicates) == 1:
        shapes.add((property_shape, SH.path, predicates[0]))
    else:
        # SHACL sequence paths require a blank-node list head.
        # An IRI here is interpreted as one predicate, not a sequence.
        shacl_path = BNode()
        Collection(shapes, shacl_path, predicates)
        shapes.add((property_shape, SH.path, shacl_path))

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shapes.serialize(destination=destination, format="turtle", encoding="utf-8")

    # Publish successful downstream knowledge only after the artifact is saved.
    _copy(bound_graph, output_graph)
    # Preserve the governed behavior without merging implementation-registry facts.
    # The generated shape retains its provenance link to the selected pattern.
    _copy(shapes, output_graph)
    result = exchange_successful_construction_stage_result(
        exchange_graph=output_graph,
        constraint_id=str(constraint),
        construction_stage="shacl-representation",
    )
    output_graph.add((result.result_id, UADEX.stageKnowledge, shape))
    return result


__all__ = ["generate_governed_constraint_shacl"]
