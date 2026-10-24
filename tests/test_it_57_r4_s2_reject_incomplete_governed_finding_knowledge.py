"""IT-57R4S2: incomplete governed finding knowledge requires review."""

from __future__ import annotations

from uuid import uuid4

import pytest
from rdflib import BNode, Graph, Literal, Namespace, RDF, URIRef
from rdflib.compare import isomorphic
from rdflib.namespace import PROV, SH

from app.services.validation_finding_projection import project_governed_findings


CV = Namespace("https://dynamicontology.com/uad36/constraint-vocabulary#")
REQUIRED_PREDICATES = (CV.sourceConstraint, CV.umdpRule, CV.severity, CV.violationKind)


@pytest.mark.parametrize(
    "missing_predicates",
    [(predicate,) for predicate in REQUIRED_PREDICATES] + [REQUIRED_PREDICATES],
    ids=["source-constraint", "source-rule", "severity", "violation-kind", "all-required-fields"],
)
def test_it_57_r4_s2_rejects_incomplete_governed_finding_knowledge(
    missing_predicates: tuple[URIRef, ...],
) -> None:
    ns = Namespace(f"urn:uad36:test:it57r4s2:{uuid4().hex}:")
    constraint = ns.constraint
    validation_result = BNode()
    field_values = {
        CV.sourceConstraint: ns.source,
        CV.umdpRule: ns.source_rule,
        CV.severity: Literal("Fatal"),
        CV.violationKind: ns.GovernedViolationKind,
    }
    governed = Graph()
    for triple in (
        (constraint, RDF.type, CV.NormalizedConstraint),
        (constraint, CV.requirementText, Literal("Apply the governed requirement.")),
        (constraint, CV.violationCondition, Literal("The governed requirement is violated.")),
        (constraint, PROV.wasDerivedFrom, ns.source),
        (ns.shape, RDF.type, SH.PropertyShape),
        (ns.shape, CV.implementsConstraint, constraint),
        (ns.shape, SH.path, ns.value_predicate),
        (ns.shape, SH.minCount, Literal(1)),
        (ns.shape, SH.message, Literal("Diagnostic text is not replacement governed knowledge.")),
    ):
        governed.add(triple)
    for predicate, value in field_values.items():
        if predicate not in missing_predicates:
            governed.add((constraint, predicate, value))
        # Another complete constraint is not a source of fallback values.
        governed.add((ns.other_constraint, predicate, value))
    governed.add((ns.other_constraint, RDF.type, CV.NormalizedConstraint))

    report = Graph()
    for triple in (
        (ns.report, RDF.type, SH.ValidationReport),
        (ns.report, SH.conforms, Literal(False)),
        (ns.report, SH.result, validation_result),
        (validation_result, RDF.type, SH.ValidationResult),
        (validation_result, SH.sourceShape, ns.shape),
        (validation_result, SH.focusNode, ns.appraisal_property),
        (validation_result, SH.resultSeverity, SH.Violation),
        (validation_result, SH.sourceConstraintComponent, SH.MinCountConstraintComponent),
    ):
        report.add(triple)
    # Even matching-looking fields in the runtime report are not authoritative.
    for predicate, value in field_values.items():
        report.add((validation_result, predicate, value))
    report_before = set(report)
    governed_before = set(governed)

    projected = project_governed_findings(
        shacl_result_graph=report,
        governed_constraint_graph=governed,
    )
    assert projected.findings == [], "Do not return an incomplete or inferred finding."
    assert set(report) == report_before
    assert set(governed) == governed_before
    exceptions = set(projected.exception_graph.subjects(RDF.type, CV.ReportFindingException))
    assert len(exceptions) == 1, (
        "IT-57R4S2 requires an explicit report-finding exception for missing "
        "governed knowledge, identifying the constraint and every missing "
        "field and routing the constraint for review. Silent omission is insufficient."
    )
    exception = next(iter(exceptions))
    graph = projected.exception_graph
    assert isinstance(exception, URIRef)
    assert set(graph.objects(exception, CV.stage)) == {Literal("report-finding")}
    assert set(graph.objects(exception, CV.status)) == {Literal("EXCEPTION")}
    assert set(graph.objects(exception, CV.governedConstraint)) == {constraint}
    assert set(graph.objects(exception, CV.shaclValidationResult)) == {validation_result}
    assert set(graph.objects(exception, CV.missingGovernedKnowledge)) == set(missing_predicates)
    assert set(graph.objects(exception, CV.requiresReview)) == {Literal(True)}
    assert (exception, PROV.wasDerivedFrom, validation_result) in graph
    reasons = list(graph.objects(exception, CV.exceptionReason))
    assert len(reasons) == 1 and isinstance(reasons[0], Literal)
    assert str(reasons[0]).strip()
    for predicate in missing_predicates:
        assert not list(graph.objects(constraint, predicate)), (
            "Exception recording must not invent a missing governed value."
        )
        assert not list(graph.objects(exception, predicate))
    assert not list(graph.subjects(RDF.type, CV.GovernedValidationFinding))
    restored = Graph().parse(data=graph.serialize(format="turtle"), format="turtle")
    assert isomorphic(graph, restored)
