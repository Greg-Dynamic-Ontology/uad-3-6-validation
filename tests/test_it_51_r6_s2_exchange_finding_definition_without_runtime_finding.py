"""IT-51R6S2: exchange a finding definition without creating a runtime finding."""

from __future__ import annotations

from uuid import uuid4

from rdflib import Graph, Literal, RDF, URIRef

from app.services.construction_exchange import (
    UADEX,
    exchange_finding_definition_knowledge,
    record_construction_stage_result,
)


FINDING_DEFINITION_TYPE = URIRef(
    "https://dynamicontology.com/uad36/"
    "constraint-vocabulary#FindingDefinition"
)
SHACL_VALIDATION_RESULT = URIRef(
    "http://www.w3.org/ns/shacl#ValidationResult"
)


def test_it_51_r6_s2_exchanges_finding_definition_without_runtime_finding() -> None:
    """Finding-definition knowledge stays construction data, not a validation result."""
    graph = Graph()
    suffix = uuid4().hex
    constraint_id = f"urn:uad36:normalized-constraint:{suffix}"
    finding_definition_id = URIRef(
        f"urn:uad36:finding-definition:{suffix}"
    )
    description = f"Describe a future validation finding: {suffix}"

    graph.add((finding_definition_id, RDF.type, FINDING_DEFINITION_TYPE))
    graph.add(
        (
            finding_definition_id,
            URIRef("urn:uad36:finding-definition-vocabulary#description"),
            Literal(description),
        )
    )

    result = record_construction_stage_result(
        output_graph=graph,
        constraint_id=constraint_id,
        construction_stage="finding-definition",
        construction_status="GREEN",
    )

    exchanged = exchange_finding_definition_knowledge(
        exchange_graph=graph,
        result_id=str(result.result_id),
        finding_definition_id=str(finding_definition_id),
    )

    assert (
        result.result_id,
        RDF.type,
        UADEX.ConstructionStageResult,
    ) in graph
    assert (
        result.result_id,
        UADEX.stageKnowledge,
        finding_definition_id,
    ) in graph
    assert (
        finding_definition_id,
        RDF.type,
        FINDING_DEFINITION_TYPE,
    ) in graph
    assert (
        finding_definition_id,
        URIRef("urn:uad36:finding-definition-vocabulary#description"),
        Literal(description),
    ) in graph
    assert (
        result.result_id,
        RDF.type,
        SHACL_VALIDATION_RESULT,
    ) not in graph
    assert (
        finding_definition_id,
        RDF.type,
        SHACL_VALIDATION_RESULT,
    ) not in graph
    assert exchanged.result_id == result.result_id
    assert exchanged.finding_definition_id == finding_definition_id