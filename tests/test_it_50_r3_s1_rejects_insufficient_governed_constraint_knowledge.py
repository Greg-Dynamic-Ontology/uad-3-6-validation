"""IT-50R3S1 — reject governed input with insufficient required knowledge."""

from __future__ import annotations

from rdflib import Graph

from app.services.constraint_normalization_agent import (
    NORMALIZATION_STAGE,
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


def test_it_50_r3_s1_rejects_insufficient_governed_source_knowledge() -> None:
    """An empty required source value must not produce normalized RDF."""

    insufficient_source = dict(GOVERNED_SOURCE)
    insufficient_source["requirement_text"] = ""

    output_graph = Graph()
    result = execute_constraint_normalization(
        governed_source=insufficient_source,
        output_graph=output_graph,
    )

    assert result.status == "exception", (
        "A governed row with an empty required requirement text must be "
        "rejected, not normalized."
    )
    assert result.output is None
    assert len(output_graph) == 0

    exception = result.exception
    assert exception is not None
    assert exception.kind == "insufficient-governed-knowledge"
    assert exception.constraint_id == "0100.0007"
    assert exception.stage == NORMALIZATION_STAGE
    assert exception.requires_review is True
    assert "requirement_text" in exception.message