"""IT-57R4S1: an untraceable SHACL result produces exception RDF, not silence."""

from __future__ import annotations

from uuid import uuid4

import pytest
from rdflib import BNode, Dataset, Graph, Literal, Namespace, RDF, URIRef
from rdflib.compare import isomorphic
from rdflib.namespace import PROV, SH

from app.services.validation_finding_projection import project_governed_findings


CV = Namespace("https://dynamicontology.com/uad36/constraint-vocabulary#")


@pytest.mark.parametrize(
    "owned_property_shape", [False, True], ids=["unmapped-shape", "unmapped-owner"]
)
def test_it_57_r4_s1_rejects_untraceable_shacl_validation_result(
    owned_property_shape: bool,
) -> None:
    ns = Namespace(f"urn:uad36:test:it57r4s1:{uuid4().hex}:")
    validation_result = BNode()
    report = Graph()
    for triple in (
        (ns.report, RDF.type, SH.ValidationReport),
        (ns.report, SH.conforms, Literal(False)),
        (ns.report, SH.result, validation_result),
        (validation_result, RDF.type, SH.ValidationResult),
        (validation_result, SH.sourceShape, ns.property_shape),
        (validation_result, SH.focusNode, ns.appraisal_property),
        (validation_result, SH.resultPath, ns.value_predicate),
        (validation_result, SH.resultSeverity, SH.Violation),
        (validation_result, SH.sourceConstraintComponent, SH.MinCountConstraintComponent),
    ):
        report.add(triple)

    governed = Graph()
    governed.add((ns.property_shape, RDF.type, SH.PropertyShape))
    governed.add((ns.property_shape, SH.path, ns.value_predicate))
    governed.add((ns.property_shape, SH.minCount, Literal(1)))
    if owned_property_shape:
        governed.add((ns.owner_shape, RDF.type, SH.NodeShape))
        governed.add((ns.owner_shape, SH.property, ns.property_shape))
    # A complete unrelated governed constraint must not become a fallback.
    for triple in (
        (ns.other_constraint, RDF.type, CV.NormalizedConstraint),
        (ns.other_constraint, CV.sourceConstraint, ns.other_source),
        (ns.other_constraint, CV.umdpRule, ns.other_rule),
        (ns.other_constraint, CV.severity, Literal("Fatal")),
        (ns.other_constraint, CV.violationKind, ns.OtherGovernedViolation),
    ):
        governed.add(triple)
    report_before = set(report)
    governed_before = set(governed)

    projected = project_governed_findings(
        shacl_result_graph=report,
        governed_constraint_graph=governed,
    )
    assert projected.findings == []
    assert set(report) == report_before
    assert set(governed) == governed_before
    exception_graph = getattr(projected, "exception_graph", None)
    assert isinstance(exception_graph, Graph), (
        "IT-57R4S1 requires the projection result to expose exception_graph "
        "containing governed report-finding exception RDF. An untraceable "
        "SHACL violation must not be silently discarded as if validation conformed."
    )
    exceptions = set(exception_graph.subjects(RDF.type, CV.ReportFindingException))
    assert len(exceptions) == 1
    exception = next(iter(exceptions))
    assert isinstance(exception, URIRef)
    assert set(exception_graph.objects(exception, CV.stage)) == {Literal("report-finding")}
    assert set(exception_graph.objects(exception, CV.status)) == {Literal("EXCEPTION")}
    assert set(exception_graph.objects(exception, CV.shaclValidationResult)) == {
        validation_result
    }, "Preserve the exact source result identity, including blank-node identity."
    assert (exception, PROV.wasDerivedFrom, validation_result) in exception_graph
    reasons = list(exception_graph.objects(exception, CV.exceptionReason))
    assert len(reasons) == 1
    assert isinstance(reasons[0], Literal) and str(reasons[0]).strip()
    assert not list(exception_graph.objects(exception, CV.governedConstraint))
    assert not list(exception_graph.objects(exception, CV.sourceConstraint))
    assert not list(exception_graph.subjects(RDF.type, CV.NormalizedConstraint))
    assert not list(exception_graph.subjects(RDF.type, CV.GovernedValidationFinding))
    assert not list(exception_graph.subject_objects(CV.implementsConstraint))

    # Copy exception RDF into a named batch graph and check that its complete
    # knowledge survives serialization. No diagnostic files are written.
    batch = Dataset().graph(ns.batch_results)
    for triple in exception_graph:
        batch.add(triple)
    restored = Graph().parse(data=batch.serialize(format="turtle"), format="turtle")
    assert isomorphic(batch, restored)
    assert len(set(restored.subjects(RDF.type, CV.ReportFindingException))) == 1
