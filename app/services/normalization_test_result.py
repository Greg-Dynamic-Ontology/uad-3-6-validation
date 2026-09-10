"""Governed normalization test-result knowledge for IT-36R6."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

from rdflib import Graph, Literal, Namespace, RDF, URIRef
from rdflib.namespace import PROV


UADTEST = Namespace("https://dynamicontology.com/uad36/test/")
UADCV = Namespace("https://dynamicontology.com/uad36/constraint-vocabulary#")
UADCON = Namespace("https://dynamicontology.com/uad36/constraint/")


@dataclass(frozen=True)
class NormalizationTestResult:
    """Identifiers and governed values produced when a test result is recorded."""

    test_result_id: URIRef
    test_execution_id: URIRef
    governed_source_id: URIRef
    scenario_id: str
    status: str
    constraint_id: str
    failure_reason: str | None = None
    warnings: tuple[str, ...] = ()


def _source_entity_id(governed_source: str) -> URIRef:
    digest = sha256(governed_source.encode("utf-8")).hexdigest()
    return URIRef(f"{UADTEST}governed-source/{digest}")


def record_normalization_test_result(
    *,
    output_graph: Graph,
    scenario_id: str,
    status: str,
    constraint_id: str,
    governed_source: str,
    failure_reason: str | None = None,
    warnings: list[str] | tuple[str, ...] | None = None,
) -> NormalizationTestResult:
    """Record a normalization test result and its PROV-O execution provenance."""
    if not scenario_id.strip():
        raise ValueError("scenario_id is required")
    if not status.strip():
        raise ValueError("status is required")
    if not constraint_id.strip():
        raise ValueError("constraint_id is required")
    if not governed_source.strip():
        raise ValueError("governed_source is required")

    normalized_status = status.strip().upper()
    normalized_warnings = tuple(warnings or ())

    if normalized_status == "RED":
        if failure_reason is None or not failure_reason.strip():
            raise ValueError("failure_reason is required for a RED test result")

    test_result_id = URIRef(
        f"{UADTEST}result/{scenario_id}/{constraint_id}/{normalized_status}"
    )
    test_execution_id = URIRef(
        f"{UADTEST}execution/{scenario_id}/{constraint_id}/{normalized_status}"
    )
    governed_source_id = _source_entity_id(governed_source)
    constraint_iri = URIRef(f"{UADCON}{constraint_id}")

    output_graph.add((test_result_id, RDF.type, UADCV.TestResult))
    output_graph.add(
        (test_result_id, UADCV.scenarioId, Literal(scenario_id))
    )
    output_graph.add(
        (test_result_id, UADCV.testStatus, Literal(normalized_status))
    )
    output_graph.add(
        (test_result_id, UADCV.forConstraint, constraint_iri)
    )
    if failure_reason is not None:
        output_graph.add(
            (test_result_id, UADCV.failureReason, Literal(failure_reason))
        )

    for warning in normalized_warnings:
        output_graph.add(
            (test_result_id, UADCV.testWarning, Literal(warning))
        )

    output_graph.add(
        (test_result_id, PROV.wasGeneratedBy, test_execution_id)
    )

    output_graph.add((test_execution_id, RDF.type, PROV.Activity))
    output_graph.add(
        (test_execution_id, PROV.used, governed_source_id)
    )

    output_graph.add((governed_source_id, RDF.type, PROV.Entity))
    output_graph.add(
        (
            governed_source_id,
            UADCV.sourceLocator,
            Literal(governed_source),
        )
    )

    return NormalizationTestResult(
        test_result_id=test_result_id,
        test_execution_id=test_execution_id,
        governed_source_id=governed_source_id,
        scenario_id=scenario_id,
        status=normalized_status,
        constraint_id=constraint_id,
        failure_reason=failure_reason,
        warnings=normalized_warnings,
    )


__all__ = [
    "NormalizationTestResult",
    "record_normalization_test_result",
]
