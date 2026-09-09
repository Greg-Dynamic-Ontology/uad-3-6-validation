"""IT-36R2S1 — preserve governed meaning independently of implementation technology."""

from __future__ import annotations

from importlib import import_module

from rdflib import Graph, Literal, Namespace, URIRef


UADCON = Namespace("https://dynamicontology.com/uad36/constraint/")
UADCV = Namespace("https://dynamicontology.com/uad36/constraint-vocabulary#")


def _load_normalization_agent():
    """Load the production normalization behavior after the RED test exists."""
    try:
        module = import_module("app.services.constraint_normalization_agent")
    except ModuleNotFoundError:
        return None

    return getattr(module, "normalize_governed_constraint", None)


def test_it_36_r2_s1_preserves_governed_meaning_independently_of_implementation_technology() -> None:
    """
    Feature: 1 Normalize governed constraints

    Rule: Normalization must not replace governed source knowledge with
    implementation-specific knowledge

    Scenario: Preserve governed meaning independently of implementation technology
    """
    normalize_governed_constraint = _load_normalization_agent()

    assert normalize_governed_constraint is not None, (
        "IT-36R2S1 requires "
        "app.services.constraint_normalization_agent."
        "normalize_governed_constraint"
    )

    governed_source = {
        "unique_id": "0100.0009",
        "data_point_name": "CityName",
        "source_rule_id": "UAD1002",
        "requirement_text": (
            "Provide the city name for the subject property physical address."
        ),
        "violation_condition": "If CityName is not provided",
        "severity": "Fatal",
        "context_fields": [
            "Subject",
            "Subject Property",
            "{No Subsection}",
            "Physical Address",
            "CityName",
        ],
        "source_locator": (
            "='[Appendix H-1 UAD Compliance Rules - URAR.xlsm]"
            "UAD Compliance Rules(Marked up)'!$A$3:$Q$3"
        ),
    }

    graph = Graph()

    normalize_governed_constraint(
        governed_source=governed_source,
        output_graph=graph,
    )

    constraint_id = URIRef(f"{UADCON}0100.0009")

    # Governed meaning survives normalization as governed knowledge.
    assert (
        constraint_id,
        UADCV.requirementText,
        Literal(governed_source["requirement_text"]),
    ) in graph
    assert (
        constraint_id,
        UADCV.violationCondition,
        Literal(governed_source["violation_condition"]),
    ) in graph
    assert (
        constraint_id,
        UADCV.severity,
        Literal(governed_source["severity"]),
    ) in graph

    # Normalization does not substitute an executable implementation for that
    # meaning. These implementation decisions belong to downstream stages.
    forbidden_predicates = {
        UADCV.shaclShape,
        UADCV.shaclPath,
        UADCV.shaclConstraintComponent,
        UADCV.pythonImplementation,
        UADCV.sparqlImplementation,
    }

    for predicate in forbidden_predicates:
        assert not list(graph.triples((constraint_id, predicate, None))), (
            f"Normalization introduced implementation-specific knowledge: {predicate}"
        )

    # No SHACL vocabulary is introduced anywhere by normalization.
    shacl_namespace = "http://www.w3.org/ns/shacl#"
    for subject, predicate, object_ in graph:
        assert not str(subject).startswith(shacl_namespace)
        assert not str(predicate).startswith(shacl_namespace)
        assert not (
            isinstance(object_, URIRef)
            and str(object_).startswith(shacl_namespace)
        )
