"""Project SHACL validation results into governed validation findings."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4

from rdflib import BNode, Graph, Literal, Namespace, RDF, URIRef
from rdflib.namespace import PROV


SH = Namespace("http://www.w3.org/ns/shacl#")
UADCV = Namespace("https://dynamicontology.com/uad36/constraint-vocabulary#")


@dataclass(frozen=True)
class GovernedValidationFinding:
    """Domain-level finding derived from SHACL and governed constraint knowledge."""

    governed_constraint: URIRef
    source_constraint: URIRef
    umdp_rule: URIRef
    severity: str
    violation_kind: URIRef
    focus_node: URIRef | BNode
    shacl_validation_result: URIRef | BNode


@dataclass(frozen=True)
class GovernedFindingProjectionResult:
    """Collection of governed findings produced from SHACL validation results."""

    findings: list[GovernedValidationFinding]
    exception_graph: Graph = field(default_factory=Graph)


def _record_report_finding_exception(
    *,
    exception_graph: Graph,
    validation_result: URIRef | BNode,
    reason: str,
) -> URIRef:
    """Record a projection exception without inventing governed knowledge."""
    exception = URIRef(
        "https://dynamicontology.com/uad36/report-finding/exception/" + uuid4().hex
    )
    exception_graph.bind("cv", UADCV)
    exception_graph.bind("prov", PROV)
    for triple in (
        (exception, RDF.type, UADCV.ReportFindingException),
        (exception, UADCV.stage, Literal("report-finding")),
        (exception, UADCV.status, Literal("EXCEPTION")),
        (exception, UADCV.shaclValidationResult, validation_result),
        (exception, UADCV.exceptionReason, Literal(reason)),
        (exception, PROV.wasDerivedFrom, validation_result),
    ):
        exception_graph.add(triple)
    return exception

def _governed_constraint_for_shape(
    graph: Graph,
    source_shape: URIRef | BNode,
) -> URIRef | None:
    """Follow explicit shape ownership without guessing a constraint identity."""
    pending = [source_shape]
    visited = set()
    constraints = set()
    while pending:
        shape = pending.pop()
        if shape in visited:
            continue
        visited.add(shape)
        constraints.update(graph.objects(shape, UADCV.implementsConstraint))
        pending.extend(
            owner
            for owner in graph.subjects(SH.property, shape)
            if isinstance(owner, (URIRef, BNode))
        )
    if len(constraints) != 1:
        return None
    constraint = next(iter(constraints))
    return constraint if isinstance(constraint, URIRef) else None


def project_governed_findings(
    *,
    shacl_result_graph: Graph,
    governed_constraint_graph: Graph,
) -> GovernedFindingProjectionResult:
    """Combine real SHACL result mechanics with authoritative governed meaning.

    A result may identify a property shape owned by the node shape that
    implements the constraint. Preserve result identities, including blank
    nodes; do not mint replacement identities or alter either input graph.
    """
    findings: list[GovernedValidationFinding] = []
    exception_graph = Graph()

    for validation_result in shacl_result_graph.subjects(
        RDF.type, SH.ValidationResult
    ):
        if not isinstance(validation_result, (URIRef, BNode)):
            continue
        source_shape = shacl_result_graph.value(validation_result, SH.sourceShape)
        focus_node = shacl_result_graph.value(validation_result, SH.focusNode)
        if not isinstance(source_shape, (URIRef, BNode)):
            continue
        if not isinstance(focus_node, (URIRef, BNode)):
            continue

        governed_constraint = _governed_constraint_for_shape(
            governed_constraint_graph, source_shape
        )
        if governed_constraint is None:
            _record_report_finding_exception(
                exception_graph=exception_graph,
                validation_result=validation_result,
                reason=(
                    f"SHACL source shape {source_shape} cannot be resolved "
                    "to exactly one governed constraint through explicit "
                    "shape ownership and implementsConstraint links."
                ),
            )
            continue

        source_constraint = governed_constraint_graph.value(
            governed_constraint, UADCV.sourceConstraint
        )
        umdp_rule = governed_constraint_graph.value(
            governed_constraint, UADCV.umdpRule
        )
        severity = governed_constraint_graph.value(
            governed_constraint, UADCV.severity
        )
        violation_kind = governed_constraint_graph.value(
            governed_constraint, UADCV.violationKind
        )
        missing = []
        if not isinstance(source_constraint, URIRef):
            missing.append(UADCV.sourceConstraint)
        if not isinstance(umdp_rule, URIRef):
            missing.append(UADCV.umdpRule)
        if severity is None or not str(severity).strip():
            missing.append(UADCV.severity)
        if not isinstance(violation_kind, URIRef):
            missing.append(UADCV.violationKind)
        if missing:
            exception = _record_report_finding_exception(
                exception_graph=exception_graph,
                validation_result=validation_result,
                reason=(
                    f"Governed constraint {governed_constraint} lacks required "
                    "finding knowledge for: " + ", ".join(map(str, missing))
                    + ". No finding was produced; governance review is required."
                ),
            )
            exception_graph.add(
                (exception, UADCV.governedConstraint, governed_constraint)
            )
            exception_graph.add((exception, UADCV.requiresReview, Literal(True)))
            for predicate in missing:
                exception_graph.add(
                    (exception, UADCV.missingGovernedKnowledge, predicate)
                )
            continue

        findings.append(
            GovernedValidationFinding(
                governed_constraint=governed_constraint,
                source_constraint=source_constraint,
                umdp_rule=umdp_rule,
                severity=str(severity),
                violation_kind=violation_kind,
                focus_node=focus_node,
                shacl_validation_result=validation_result,
            )
        )

    return GovernedFindingProjectionResult(
        findings=findings,
        exception_graph=exception_graph,
    )


__all__ = [
    "GovernedFindingProjectionResult",
    "GovernedValidationFinding",
    "project_governed_findings",
]
