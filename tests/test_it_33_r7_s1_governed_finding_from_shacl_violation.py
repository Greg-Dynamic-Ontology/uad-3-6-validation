"""IT-33R7S1 — produce a governed finding from a SHACL violation."""

from __future__ import annotations

from importlib import import_module

from rdflib import Graph, Literal, Namespace, RDF, URIRef


SH = Namespace("http://www.w3.org/ns/shacl#")
UADCV = Namespace("https://dynamicontology.com/uad36/constraint-vocabulary#")


def _load_finding_projection_service():
    """Load the production finding-projection service after RED exists."""
    try:
        module = import_module("app.services.validation_finding_projection")
    except ModuleNotFoundError:
        return None

    return getattr(module, "project_governed_findings", None)


def test_it_33_r7_s1_produces_governed_finding_from_shacl_violation() -> None:
    """
    Feature: Build governed validation constraints at scale

    Rule: Project SHACL validation results into governed validation findings

    Scenario: Produce a governed finding from a SHACL violation
    """
    project_governed_findings = _load_finding_projection_service()

    assert project_governed_findings is not None, (
        "IT-33R7S1 requires "
        "app.services.validation_finding_projection."
        "project_governed_findings"
    )

    shacl_result_graph = Graph()
    governed_constraint_graph = Graph()

    validation_result = URIRef(
        "https://dynamicontology.com/uad36/test/shacl-result/1"
    )
    source_shape = URIRef(
        "https://dynamicontology.com/uad36/shape/0100.0007"
    )
    focus_node = URIRef(
        "https://dynamicontology.com/uad36/test/it-32-r1-c1/subject-property"
    )
    normalized_constraint = URIRef(
        "https://dynamicontology.com/uad36/constraint/0100.0007"
    )
    source_constraint = URIRef(
        "https://dynamicontology.com/uad36/"
        "source/umdp/fannie-mae/constraint/0100.0007"
    )
    umdp_rule = URIRef(
        "https://dynamicontology.com/uad36/"
        "source/umdp/fannie-mae/rule/UAD1001"
    )

    shacl_result_graph.add(
        (validation_result, RDF.type, SH.ValidationResult)
    )
    shacl_result_graph.add(
        (validation_result, SH.sourceShape, source_shape)
    )
    shacl_result_graph.add(
        (validation_result, SH.focusNode, focus_node)
    )

    governed_constraint_graph.add(
        (
            source_shape,
            UADCV.implementsConstraint,
            normalized_constraint,
        )
    )
    governed_constraint_graph.add(
        (
            normalized_constraint,
            UADCV.sourceConstraint,
            source_constraint,
        )
    )
    governed_constraint_graph.add(
        (
            normalized_constraint,
            UADCV.umdpRule,
            umdp_rule,
        )
    )
    governed_constraint_graph.add(
        (
            normalized_constraint,
            UADCV.severity,
            Literal("Fatal"),
        )
    )
    governed_constraint_graph.add(
        (
            normalized_constraint,
            UADCV.violationKind,
            UADCV.MissingRequiredValue,
        )
    )

    result = project_governed_findings(
        shacl_result_graph=shacl_result_graph,
        governed_constraint_graph=governed_constraint_graph,
    )

    # One SHACL violation produces one governed validation finding.
    assert len(result.findings) == 1
    finding = result.findings[0]

    # The finding identifies the governed constraint.
    assert finding.governed_constraint == normalized_constraint

    # The finding identifies the governed source constraint.
    assert finding.source_constraint == source_constraint

    # The finding identifies the UMDP rule.
    assert finding.umdp_rule == umdp_rule

    # The finding reports governed severity.
    assert finding.severity == "Fatal"

    # The finding reports the governed violation kind.
    assert finding.violation_kind == UADCV.MissingRequiredValue

    # The finding identifies the focus of the SHACL violation.
    assert finding.focus_node == focus_node

    # The finding remains traceable to the original SHACL validation result.
    assert finding.shacl_validation_result == validation_result
