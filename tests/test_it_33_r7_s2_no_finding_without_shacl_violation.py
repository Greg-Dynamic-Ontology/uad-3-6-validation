"""IT-33R7S2 — produce no governed finding when SHACL reports no violation."""

from __future__ import annotations

from importlib import import_module

from rdflib import Graph


def _load_finding_projection_service():
    """Load the production finding-projection service after RED exists."""
    try:
        module = import_module("app.services.validation_finding_projection")
    except ModuleNotFoundError:
        return None

    return getattr(module, "project_governed_findings", None)


def test_it_33_r7_s2_produces_no_governed_finding_when_shacl_reports_no_violation() -> None:
    """
    Feature: Build governed validation constraints at scale

    Rule: Project SHACL validation results into governed validation findings

    Scenario: Produce no governed finding when SHACL reports no violation
    """
    project_governed_findings = _load_finding_projection_service()

    assert project_governed_findings is not None, (
        "IT-33R7S2 requires "
        "app.services.validation_finding_projection."
        "project_governed_findings"
    )

    shacl_result_graph = Graph()
    governed_constraint_graph = Graph()

    result = project_governed_findings(
        shacl_result_graph=shacl_result_graph,
        governed_constraint_graph=governed_constraint_graph,
    )

    # No SHACL ValidationResult means no governed validation finding.
    assert result.findings == []
