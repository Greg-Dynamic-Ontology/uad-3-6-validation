"""IT-37R5S1 — carry normalized constraint knowledge as a stage-specific result."""

from __future__ import annotations

from importlib import import_module

from rdflib import Graph, Literal, Namespace, RDF, URIRef


UADEX = Namespace("https://dynamicontology.com/uad36/construction-exchange#")
UADCV = Namespace("https://dynamicontology.com/uad36/constraint-vocabulary#")


def _load_stage_specific_exchange():
    """Load stage-specific exchange behavior after RED exists."""
    try:
        module = import_module("app.services.construction_exchange")
    except ModuleNotFoundError:
        return None

    return getattr(module, "carry_stage_specific_knowledge", None)


def test_it_37_r5_s1_carries_normalized_constraint_as_stage_specific_result() -> None:
    """
    Feature: Define governed RDF exchange between constraint-construction stages

    Rule: Stage-specific knowledge is carried within a common exchange contract

    Scenario: Carry normalized constraint knowledge as a stage-specific result
    """
    carry_stage_specific_knowledge = _load_stage_specific_exchange()

    assert carry_stage_specific_knowledge is not None, (
        "IT-37R5S1 requires "
        "app.services.construction_exchange."
        "carry_stage_specific_knowledge"
    )

    graph = Graph()

    result_id = URIRef(
        "https://dynamicontology.com/uad36/construction-exchange/"
        "result/0100.0009-normalization"
    )
    normalized_constraint_id = URIRef(
        "https://dynamicontology.com/uad36/constraint/0100.0009"
    )

    graph.add((result_id, RDF.type, UADEX.ConstructionStageResult))
    graph.add(
        (
            result_id,
            UADEX.constructionStage,
            Literal("normalized-constraint-representation"),
        )
    )
    graph.add(
        (
            normalized_constraint_id,
            RDF.type,
            UADCV.NormalizedConstraint,
        )
    )
    graph.add(
        (
            normalized_constraint_id,
            UADCV.governedUniqueId,
            Literal("0100.0009"),
        )
    )
    graph.add(
        (
            normalized_constraint_id,
            UADCV.dataPointName,
            Literal("CityName"),
        )
    )

    normalized_before = set(
        graph.triples((normalized_constraint_id, None, None))
    )

    result = carry_stage_specific_knowledge(
        exchange_graph=graph,
        result_id=str(result_id),
        stage_knowledge_id=str(normalized_constraint_id),
        expected_stage="normalized-constraint-representation",
        expected_knowledge_type=str(UADCV.NormalizedConstraint),
    )

    assert result.result_id == result_id
    assert result.stage_knowledge_id == normalized_constraint_id

    assert (
        result_id,
        UADEX.stageKnowledge,
        normalized_constraint_id,
    ) in graph

    assert (
        normalized_constraint_id,
        RDF.type,
        UADCV.NormalizedConstraint,
    ) in graph

    # Common exchange metadata links to the normalized constraint; it does not
    # replace, flatten, or rewrite the normalized constraint knowledge.
    assert normalized_before.issubset(
        set(graph.triples((normalized_constraint_id, None, None)))
    )
