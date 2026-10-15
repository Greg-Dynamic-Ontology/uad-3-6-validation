"""IT-50R4S1 — return only contracted output or a contracted exception."""

from __future__ import annotations

from dataclasses import fields

from rdflib import Graph, Literal, RDF, URIRef

from app.services.constraint_normalization_agent import (
    NORMALIZATION_STAGE,
    UADCON,
    UADCV,
    ConstraintNormalizationExecutionResult,
    NormalizationException,
    NormalizedConstraintResult,
    execute_constraint_normalization,
)


GOVERNED_SOURCE = {
    "unique_id": "0100.0007",
    "data_point_name": "AddressLineText",
    "source_rule_id": "UAD1001",
    "requirement_text": (
        "Provide the address line for the subject property physical address."
    ),
    "violation_condition": "If AddressLineText is not provided",
    "severity": "Fatal",
    "context_fields": [
        "Subject",
        "Subject Property",
        "{No Subsection}",
        "Physical Address",
        "AddressLineText",
    ],
    "source_locator": "data-constraints.csv#row=2",
    "source_constraint_uri": (
        "https://dynamicontology.com/uad36/source/umdp/"
        "fannie-mae/constraint/0100.0007"
    ),
}


NORMALIZED_PREDICATES = {
    RDF.type,
    UADCV.governedUniqueId,
    UADCV.dataPointName,
    UADCV.sourceRuleId,
    UADCV.requirementText,
    UADCV.violationCondition,
    UADCV.severity,
    UADCV.sourceLocator,
    UADCV.hasSourceContext,
    UADCV.contextOrder,
    UADCV.contextValue,
}


def test_it_50_r4_s1_returns_only_contracted_output_or_exception() -> None:
    """Success and insufficiency return only the bounded worker's contract."""
    downstream_sentinel = (
        URIRef("urn:test:logical-schema-binding"),
        URIRef("urn:test:downstream-predicate"),
        Literal("must remain untouched"),
    )

    successful_graph = Graph()
    successful_graph.add(downstream_sentinel)

    success = execute_constraint_normalization(
        governed_source=dict(GOVERNED_SOURCE),
        output_graph=successful_graph,
    )

    assert type(success) is ConstraintNormalizationExecutionResult
    assert success.status == "success"
    assert type(success.output) is NormalizedConstraintResult
    assert success.exception is None
    assert {field.name for field in fields(success)} == {
        "status",
        "output",
        "exception",
    }
    assert {field.name for field in fields(success.output)} == {
        "constraint_id",
        "unique_id",
        "data_point_name",
        "source_rule_id",
    }
    assert success.output.unique_id == "0100.0007"
    assert success.output.data_point_name == "AddressLineText"
    assert success.output.source_rule_id == "UAD1001"
    assert downstream_sentinel in successful_graph

    normalized_triples = set(successful_graph) - {downstream_sentinel}
    assert normalized_triples
    assert all(predicate in NORMALIZED_PREDICATES
               for _, predicate, _ in normalized_triples)
    assert all(
        str(subject).startswith(str(UADCON))
        for subject, _, _ in normalized_triples
    )

    insufficient_source = dict(GOVERNED_SOURCE)
    insufficient_source["requirement_text"] = ""

    exception_graph = Graph()
    exception_graph.add(downstream_sentinel)

    failure = execute_constraint_normalization(
        governed_source=insufficient_source,
        output_graph=exception_graph,
    )

    assert type(failure) is ConstraintNormalizationExecutionResult
    assert failure.status == "exception"
    assert failure.output is None
    assert type(failure.exception) is NormalizationException
    assert {field.name for field in fields(failure.exception)} == {
        "kind",
        "constraint_id",
        "stage",
        "requires_review",
        "message",
    }
    assert failure.exception.kind == "insufficient-governed-knowledge"
    assert failure.exception.constraint_id == "0100.0007"
    assert failure.exception.stage == NORMALIZATION_STAGE
    assert failure.exception.requires_review is True
    assert "requirement_text" in failure.exception.message
    assert set(exception_graph) == {downstream_sentinel}