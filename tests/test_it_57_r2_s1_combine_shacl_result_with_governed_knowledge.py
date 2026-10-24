"""IT-57R2S1: governed meaning takes precedence over SHACL diagnostics."""

from __future__ import annotations

from uuid import uuid4

import pytest
from rdflib import BNode, Graph, Literal, Namespace, RDF
from rdflib.namespace import PROV, SH

from app.services.validation_finding_projection import project_governed_findings


CV = Namespace("https://dynamicontology.com/uad36/constraint-vocabulary#")


@pytest.mark.parametrize("blank_result", [False, True], ids=["iri-result", "blank-node-result"])
def test_it_57_r2_s1_combines_shacl_result_with_governed_constraint_knowledge(
    blank_result: bool,
) -> None:
    ns = Namespace(f"urn:uad36:test:it57r2s1:{uuid4().hex}:")
    constraint = ns.governed_constraint
    source = ns.source_constraint
    source_rule = ns.source_rule
    violation_kind = ns.GovernedMissingRequiredValue
    severity = "Fatal"
    focus_node = ns.appraisal_property
    validation_result = BNode() if blank_result else ns.validation_result

    governed = Graph()
    for triple in (
        (constraint, RDF.type, CV.NormalizedConstraint),
        (constraint, CV.sourceConstraint, source),
        (constraint, CV.umdpRule, source_rule),
        (constraint, CV.severity, Literal(severity)),
        (constraint, CV.violationKind, violation_kind),
        (constraint, CV.requirementText, Literal("Supply the governed required value.")),
        (constraint, CV.violationCondition, Literal("The governed required value is absent.")),
        (constraint, PROV.wasDerivedFrom, source),
        (ns.node_shape, RDF.type, SH.NodeShape),
        (ns.node_shape, CV.implementsConstraint, constraint),
        (ns.node_shape, SH.property, ns.property_shape),
        (ns.property_shape, RDF.type, SH.PropertyShape),
        (ns.property_shape, SH.path, ns.projected_value),
        (ns.property_shape, SH.minCount, Literal(1)),
        # Another complete governed record must not be selected merely because
        # it happens to be available in the same knowledge graph.
        (ns.other_constraint, RDF.type, CV.NormalizedConstraint),
        (ns.other_constraint, CV.sourceConstraint, ns.other_source),
        (ns.other_constraint, CV.umdpRule, ns.other_rule),
        (ns.other_constraint, CV.severity, Literal("Warning")),
        (ns.other_constraint, CV.violationKind, ns.OtherGovernedViolation),
    ):
        governed.add(triple)
    governed_before = set(governed)
    observed = []

    for diagnostic_severity in (SH.Warning, SH.Info):
        # Controlled runtime-report fixture: diagnostic mechanics deliberately
        # disagree with governed domain values. R1 separately exercises a real
        # pySHACL report; this scenario tests which source is authoritative.
        report = Graph()
        for triple in (
            (ns.report, RDF.type, SH.ValidationReport),
            (ns.report, SH.conforms, Literal(False)),
            (ns.report, SH.result, validation_result),
            (validation_result, RDF.type, SH.ValidationResult),
            (validation_result, SH.sourceShape, ns.property_shape),
            (validation_result, SH.focusNode, focus_node),
            (validation_result, SH.resultPath, ns.projected_value),
            (validation_result, SH.sourceConstraintComponent, SH.MinCountConstraintComponent),
            (validation_result, SH.resultSeverity, diagnostic_severity),
            (validation_result, SH.resultMessage, Literal("SHACL diagnostic: too few values.")),
            # Even domain-looking metadata in the report is not the authority.
            (validation_result, CV.sourceConstraint, ns.other_source),
            (validation_result, CV.umdpRule, ns.other_rule),
            (validation_result, CV.severity, Literal("Warning")),
            (validation_result, CV.violationKind, ns.SHACLDiagnosticKind),
        ):
            report.add(triple)
        report_before = set(report)
        projected = project_governed_findings(
            shacl_result_graph=report,
            governed_constraint_graph=governed,
        )
        assert set(report) == report_before
        assert set(governed) == governed_before
        assert len(projected.findings) == 1
        finding = projected.findings[0]

        # Mechanics come from the exact runtime result, without replacing its
        # RDF identity or substituting an unrelated instance resource.
        assert finding.shacl_validation_result == validation_result
        assert finding.focus_node == focus_node
        assert (finding.shacl_validation_result, SH.sourceShape, ns.property_shape) in report

        # Domain meaning comes exclusively from the governed constraint found
        # through the explicit generated-shape ownership relationship.
        assert finding.governed_constraint == constraint
        assert finding.source_constraint == source
        assert finding.umdp_rule == source_rule
        assert finding.severity == severity
        assert finding.violation_kind == violation_kind
        assert finding.governed_constraint not in {
            ns.node_shape, ns.property_shape, validation_result, SH.MinCountConstraintComponent
        }
        assert (finding.governed_constraint, PROV.wasDerivedFrom, finding.source_constraint) in governed
        assert (finding.governed_constraint, CV.umdpRule, finding.umdp_rule) in governed
        observed.append(finding)

    assert observed[0] == observed[1], (
        "Changing SHACL diagnostic severity must not change governed finding meaning."
    )
