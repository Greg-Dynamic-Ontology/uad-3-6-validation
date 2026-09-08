"""Project SHACL validation results into governed validation findings."""

from __future__ import annotations

from dataclasses import dataclass

from rdflib import Graph, Namespace, RDF, URIRef


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
    focus_node: URIRef
    shacl_validation_result: URIRef


@dataclass(frozen=True)
class GovernedFindingProjectionResult:
    """Collection of governed findings produced from SHACL validation results."""

    findings: list[GovernedValidationFinding]


def project_governed_findings(
    *,
    shacl_result_graph: Graph,
    governed_constraint_graph: Graph,
) -> GovernedFindingProjectionResult:
    """
    Project SHACL validation results into governed validation findings.

    Each SHACL ValidationResult is linked through its source shape to the
    normalized governed constraint. Governed meaning is then read from the
    constraint graph and combined with the SHACL focus node and result identity.
    """
    findings: list[GovernedValidationFinding] = []

    for validation_result in shacl_result_graph.subjects(
        RDF.type,
        SH.ValidationResult,
    ):
        if not isinstance(validation_result, URIRef):
            continue

        source_shape = shacl_result_graph.value(
            validation_result,
            SH.sourceShape,
        )
        focus_node = shacl_result_graph.value(
            validation_result,
            SH.focusNode,
        )

        if not isinstance(source_shape, URIRef):
            continue
        if not isinstance(focus_node, URIRef):
            continue

        governed_constraint = governed_constraint_graph.value(
            source_shape,
            UADCV.implementsConstraint,
        )
        if not isinstance(governed_constraint, URIRef):
            continue

        source_constraint = governed_constraint_graph.value(
            governed_constraint,
            UADCV.sourceConstraint,
        )
        umdp_rule = governed_constraint_graph.value(
            governed_constraint,
            UADCV.umdpRule,
        )
        severity = governed_constraint_graph.value(
            governed_constraint,
            UADCV.severity,
        )
        violation_kind = governed_constraint_graph.value(
            governed_constraint,
            UADCV.violationKind,
        )

        if not isinstance(source_constraint, URIRef):
            continue
        if not isinstance(umdp_rule, URIRef):
            continue
        if severity is None:
            continue
        if not isinstance(violation_kind, URIRef):
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

    return GovernedFindingProjectionResult(findings=findings)


__all__ = [
    "GovernedFindingProjectionResult",
    "GovernedValidationFinding",
    "project_governed_findings",
]
