"""IT-51R6S1: keep construction failure distinct from validation failure."""

from __future__ import annotations

from uuid import uuid4

import pytest
from rdflib import Graph, Literal, RDF, URIRef

from app.services.construction_exchange import (
    UADEX,
    record_construction_failure,
)


@pytest.mark.parametrize("construction_status", ["RED", "EXCEPTION"])
def test_it_51_r6_s1_keeps_construction_failure_out_of_validation_results(
    construction_status: str,
) -> None:
    """RED and exception knowledge remain construction-stage exchange results."""
    graph = Graph()
    suffix = uuid4().hex
    result_id = f"urn:uad36:construction-result:{suffix}"
    constraint_id = f"urn:uad36:normalized-constraint:{suffix}"
    construction_stage = "logical-schema-binding"
    failure_reason = f"Governed construction could not complete: {suffix}"

    failure = record_construction_failure(
        exchange_graph=graph,
        result_id=result_id,
        constraint_id=constraint_id,
        construction_stage=construction_stage,
        construction_status=construction_status,
        failure_reason=failure_reason,
    )

    result = URIRef(result_id)

    assert (result, RDF.type, UADEX.ConstructionStageResult) in graph
    assert (
        result,
        UADEX.constructionStatus,
        Literal(construction_status),
    ) in graph
    assert (
        result,
        UADEX.failureReason,
        Literal(failure_reason),
    ) in graph
    assert (
        result,
        RDF.type,
        URIRef("http://www.w3.org/ns/shacl#ValidationResult"),
    ) not in graph
    assert failure.result_id == result
    assert failure.construction_status == construction_status