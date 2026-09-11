"""IT-37R5S2 — permit later stages to define their own result knowledge."""

from __future__ import annotations

from importlib import import_module

from rdflib import Graph, Literal, Namespace, RDF, URIRef


UADEX = Namespace("https://dynamicontology.com/uad36/construction-exchange#")
UADCV = Namespace("https://dynamicontology.com/uad36/constraint-vocabulary#")


def _load_stage_specific_exchange():
    """Load stage-specific exchange behavior established by IT-37R5."""
    try:
        module = import_module("app.services.construction_exchange")
    except ModuleNotFoundError:
        return None

    return getattr(module, "carry_stage_specific_knowledge", None)


def test_it_37_r5_s2_permits_later_stages_to_define_their_own_result_knowledge() -> None:
    """
    Feature: Define governed RDF exchange between constraint-construction stages

    Rule: Stage-specific knowledge is carried within a common exchange contract

    Scenario: Permit later stages to define their own result knowledge
    """
    carry_stage_specific_knowledge = _load_stage_specific_exchange()

    assert carry_stage_specific_knowledge is not None, (
        "IT-37R5S2 requires "
        "app.services.construction_exchange."
        "carry_stage_specific_knowledge"
    )

    graph = Graph()

    result_id = URIRef(
        "https://dynamicontology.com/uad36/construction-exchange/"
        "result/0100.0009-logical-schema-binding"
    )
    binding_knowledge_id = URIRef(
        "https://dynamicontology.com/uad36/construction/"
        "logical-schema-binding/0100.0009"
    )

    graph.add((result_id, RDF.type, UADEX.ConstructionStageResult))
    graph.add(
        (
            result_id,
            UADEX.constructionStage,
            Literal("logical-schema-binding"),
        )
    )

    graph.add(
        (
            binding_knowledge_id,
            RDF.type,
            UADCV.LogicalSchemaBindingResult,
        )
    )
    graph.add(
        (
            binding_knowledge_id,
            UADCV.boundSchemaTerm,
            URIRef("https://dynamicontology.com/uad36/schema/CityName"),
        )
    )

    stage_specific_before = set(
        graph.triples((binding_knowledge_id, None, None))
    )

    result = carry_stage_specific_knowledge(
        exchange_graph=graph,
        result_id=str(result_id),
        stage_knowledge_id=str(binding_knowledge_id),
        expected_stage="logical-schema-binding",
        expected_knowledge_type=str(UADCV.LogicalSchemaBindingResult),
    )

    assert result.result_id == result_id
    assert result.stage_knowledge_id == binding_knowledge_id

    assert (
        result_id,
        UADEX.stageKnowledge,
        binding_knowledge_id,
    ) in graph

    assert (
        binding_knowledge_id,
        RDF.type,
        UADCV.LogicalSchemaBindingResult,
    ) in graph

    assert (
        binding_knowledge_id,
        UADCV.boundSchemaTerm,
        URIRef("https://dynamicontology.com/uad36/schema/CityName"),
    ) in graph

    # The common exchange contract must not flatten stage-specific RDF into text.
    assert not list(
        graph.triples(
            (
                result_id,
                UADEX.stageKnowledgeText,
                None,
            )
        )
    )

    assert stage_specific_before.issubset(
        set(graph.triples((binding_knowledge_id, None, None)))
    )
