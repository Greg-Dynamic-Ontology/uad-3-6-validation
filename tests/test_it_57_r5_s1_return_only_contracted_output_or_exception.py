"""IT-57R5S1: report-finding projection preserves its governed inputs."""

from __future__ import annotations

from uuid import uuid4

import pytest
from rdflib import BNode, Graph, Literal, Namespace, RDF
from rdflib.collection import Collection
from rdflib.namespace import PROV, SH

from app.services.validation_finding_projection import (
    GovernedFindingProjectionResult,
    GovernedValidationFinding,
    project_governed_findings,
)


CV = Namespace("https://dynamicontology.com/uad36/constraint-vocabulary#")


@pytest.mark.parametrize(
    "case,finding_count,exception_count",
    [
        ("governed-violation", 1, 0),
        ("conforming", 0, 0),
        ("untraceable", 0, 1),
        ("incomplete-knowledge", 0, 1),
    ],
    ids=["finding", "no-violation", "untraceable-exception", "incomplete-exception"],
)
def test_it_57_r5_s1_returns_only_contracted_output_or_exception(
    case: str,
    finding_count: int,
    exception_count: int,
) -> None:
    ns = Namespace(f"urn:uad36:test:it57r5s1:{uuid4().hex}:")
    constraint = ns.constraint
    validation_result = BNode()
    governed = Graph()
    for triple in (
        (constraint, RDF.type, CV.NormalizedConstraint),
        (constraint, CV.requirementText, Literal("Supply the governed required value.")),
        (constraint, CV.violationCondition, Literal("The governed required value is absent.")),
        (constraint, CV.sourceConstraint, ns.source),
        (constraint, CV.umdpRule, ns.source_rule),
        (constraint, CV.severity, Literal("Fatal")),
        (constraint, CV.violationKind, ns.MissingRequiredValue),
        (constraint, PROV.wasDerivedFrom, ns.source),
        (constraint, CV.boundLogicalSchemaResource, ns.value_qname),
        (constraint, CV.applicableContext, ns.context),
        (constraint, CV.behaviorClassification, ns.classification),
        (constraint, CV.instanceRdfBinding, ns.binding),
        (constraint, CV.shaclRepresentation, ns.node_shape),
        (ns.context, RDF.type, CV.ConstraintContext),
        (ns.context, CV.schemaPath, ns.schema_path),
        (ns.classification, RDF.type, CV.ValidationBehaviorClassification),
        (ns.classification, CV.applicableContext, ns.context),
        (ns.classification, CV.validationBehavior, ns.behavior),
        (ns.behavior, RDF.type, CV.ValidationBehavior),
        (ns.binding, RDF.type, CV.InstanceRdfBinding),
        (ns.binding, CV.boundLogicalSchemaResource, ns.value_qname),
        (ns.binding, CV.applicableContext, ns.context),
        (ns.binding, CV.behaviorClassification, ns.classification),
        (ns.binding, CV.validationBehavior, ns.behavior),
        (ns.binding, CV.focusClass, ns.Property),
        (ns.binding, CV.valuePredicate, ns.value_predicate),
        (ns.binding, CV.predicatePath, ns.predicate_path),
        (ns.node_shape, RDF.type, SH.NodeShape),
        (ns.node_shape, CV.implementsConstraint, constraint),
        (ns.node_shape, SH.targetClass, ns.Property),
        (ns.node_shape, SH.property, ns.property_shape),
        (ns.property_shape, RDF.type, SH.PropertyShape),
        (ns.property_shape, SH.path, ns.value_predicate),
        (ns.property_shape, SH.minCount, Literal(1)),
    ):
        governed.add(triple)
    Collection(governed, ns.schema_path, [ns.root_qname, ns.value_qname])
    Collection(governed, ns.predicate_path, [ns.value_predicate])
    if case == "untraceable":
        governed.remove((ns.node_shape, CV.implementsConstraint, constraint))
    if case == "incomplete-knowledge":
        governed.remove((constraint, CV.severity, None))

    report = Graph()
    report.add((ns.report, RDF.type, SH.ValidationReport))
    report.add((ns.report, SH.conforms, Literal(case == "conforming")))
    if case != "conforming":
        for triple in (
            (ns.report, SH.result, validation_result),
            (validation_result, RDF.type, SH.ValidationResult),
            (validation_result, SH.sourceShape, ns.property_shape),
            (validation_result, SH.focusNode, ns.appraisal_property),
            (validation_result, SH.resultSeverity, SH.Violation),
            (validation_result, SH.sourceConstraintComponent, SH.MinCountConstraintComponent),
        ):
            report.add(triple)
    governed_before = set(governed)
    report_before = set(report)
    projected = project_governed_findings(
        shacl_result_graph=report,
        governed_constraint_graph=governed,
    )

    assert isinstance(projected, GovernedFindingProjectionResult)
    assert isinstance(projected.findings, list)
    assert isinstance(projected.exception_graph, Graph)
    assert projected.exception_graph is not governed
    assert projected.exception_graph is not report
    assert len(projected.findings) == finding_count
    exceptions = set(projected.exception_graph.subjects(RDF.type, CV.ReportFindingException))
    assert len(exceptions) == exception_count

    # Equality of the full inputs includes all normalized meaning, bindings,
    # context lists, behavior knowledge, and executable shape statements.
    assert set(governed) == governed_before
    assert set(report) == report_before
    for finding in projected.findings:
        assert isinstance(finding, GovernedValidationFinding)
        assert finding.governed_constraint == constraint
        assert finding.source_constraint == ns.source
        assert finding.umdp_rule == ns.source_rule
        assert finding.severity == "Fatal"
        assert finding.violation_kind == ns.MissingRequiredValue
        assert finding.focus_node == ns.appraisal_property
        assert finding.shacl_validation_result == validation_result
    for exception in exceptions:
        graph = projected.exception_graph
        assert (exception, CV.stage, Literal("report-finding")) in graph
        assert (exception, CV.status, Literal("EXCEPTION")) in graph
        assert (exception, CV.shaclValidationResult, validation_result) in graph
        assert (exception, PROV.wasDerivedFrom, validation_result) in graph
        assert str(next(graph.objects(exception, CV.exceptionReason))).strip()
    if exception_count == 0:
        assert len(projected.exception_graph) == 0

    # Exceptions may record projection problems but may not generate or replace
    # construction artifacts, shapes, or additional SHACL validation results.
    for _, predicate, value in projected.exception_graph:
        assert not str(predicate).startswith(str(SH))
        if predicate == RDF.type:
            assert value == CV.ReportFindingException
