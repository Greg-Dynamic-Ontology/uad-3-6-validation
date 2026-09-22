"""IT-37R6S2 — exchange finding-definition knowledge without creating a runtime finding."""

from __future__ import annotations

from importlib import import_module

from rdflib import Graph, Literal, Namespace, RDF, URIRef


UADEX = Namespace("https://dynamicontology.com/uad36/construction-exchange#")
UADCV = Namespace("https://dynamicontology.com/uad36/constraint-vocabulary#")
SH = Namespace("http://www.w3.org/ns/shacl#")


def _load_finding_definition_exchange():
    """Load finding-definition exchange behavior after RED exists."""
    try:
        module = import_module("app.services.construction_exchange")
    except ModuleNotFoundError:
        return None

    return getattr(module, "exchange_finding_definition_knowledge", None)


def test_it_37_r6_s2_exchanges_finding_definition_without_runtime_finding() -> None:
    """
    Feature: Define governed RDF exchange between constraint-construction stages

    Rule: The exchange graph preserves the constraint-construction and
          validation-execution boundary

    Scenario: Exchange finding-definition knowledge without creating a runtime finding
    """
    exchange_finding_definition = _load_finding_definition_exchange()

    assert exchange_finding_definition is not None, (
        "IT-37R6S2 requires "
        "app.services.construction_exchange."
        "exchange_finding_definition_knowledge"
    )

    graph = Graph()

    result_id = URIRef(
        "https://dynamicontology.com/uad36/construction-exchange/"
        "result/0100.0009-finding-definition"
    )
    finding_definition_id = URIRef(
        "https://dynamicontology.com/uad36/construction/"
        "finding-definition/0100.0009"
    )

    graph.add((result_id, RDF.type, UADEX.ConstructionStageResult))
    graph.add(
        (
            result_id,
            UADEX.constructionStage,
            Literal("finding-definition"),
        )
    )
    graph.add(
        (
            finding_definition_id,
            RDF.type,
            UADCV.FindingDefinition,
        )
    )

    result = exchange_finding_definition(
        exchange_graph=graph,
        result_id=str(result_id),
        finding_definition_id=str(finding_definition_id),
    )

    assert result.result_id == result_id
    assert result.finding_definition_id == finding_definition_id

    assert (
        result_id,
        UADEX.stageKnowledge,
        finding_definition_id,
    ) in graph
    assert (
        finding_definition_id,
        RDF.type,
        UADCV.FindingDefinition,
    ) in graph

    # Finding-definition knowledge remains construction knowledge.
    # No runtime appraisal validation finding or SHACL result is created.
    assert not list(graph.subjects(RDF.type, SH.ValidationResult))
    assert not list(graph.subjects(RDF.type, SH.ValidationReport))
    assert not list(graph.subjects(RDF.type, UADCV.ValidationFinding))
