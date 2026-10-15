"""IT-50R3S2 — reject ambiguous governed source knowledge."""

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


def test_it_50_r3_s2_rejects_ambiguous_governed_source_knowledge() -> None:
    """Ambiguous candidate meanings must be preserved for review, not selected."""
    first_interpretation = (
        "Provide the address line for the subject property physical address."
    )
    second_interpretation = (
        "Provide the mailing address line for the subject property."
    )
    ambiguous_source = dict(GOVERNED_SOURCE)
    ambiguous_source["requirement_text"] = [
        first_interpretation,
        second_interpretation,
    ]

    output_graph = Graph()
    result = execute_constraint_normalization(
        governed_source=ambiguous_source,
        output_graph=output_graph,
    )

    assert result.status == "exception", (
        "Multiple incompatible requirement interpretations must be routed "
        "for review rather than normalized."
    )
    assert result.output is None
    assert len(output_graph) == 0

    exception = result.exception
    assert exception is not None
    assert exception.kind == "ambiguous-governed-knowledge"
    assert exception.constraint_id == "0100.0007"
    assert exception.stage == NORMALIZATION_STAGE
    assert exception.requires_review is True
    assert "requirement_text" in exception.message
    assert first_interpretation in exception.message, (
        "The review exception must preserve the first ambiguous candidate."
    )
    assert second_interpretation in exception.message, (
        "The review exception must preserve the second ambiguous candidate."
    )