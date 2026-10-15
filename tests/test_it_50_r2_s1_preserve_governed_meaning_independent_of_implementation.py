"""IT-50R2S1 — preserve governed meaning across implementation identifiers."""

from __future__ import annotations

from pathlib import Path

from rdflib import Graph, Literal, Namespace, RDF, URIRef

from app.services import constraint_normalization_agent


CONSTRAINT_VOCAB = Namespace(
    "https://dynamicontology.com/uad36/constraint-vocabulary#"
)
PROV = Namespace("http://www.w3.org/ns/prov#")

SOURCE_CONSTRAINT = URIRef(
    "https://dynamicontology.com/uad36/source/umdp/fannie-mae/constraint/0100.0007"
)

SOURCE_ROW = {
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
    "source_constraint_uri": str(SOURCE_CONSTRAINT),
}

GOVERNED_VALUE_PREDICATES = (
    CONSTRAINT_VOCAB.governedUniqueId,
    CONSTRAINT_VOCAB.dataPointName,
    CONSTRAINT_VOCAB.sourceRuleId,
    CONSTRAINT_VOCAB.requirementText,
    CONSTRAINT_VOCAB.violationCondition,
    CONSTRAINT_VOCAB.severity,
    CONSTRAINT_VOCAB.sourceLocator,
)


def _normalized_constraint(graph: Graph) -> URIRef:
    """Return the sole normalized constraint resource in the graph."""

    constraints = list(
        graph.subjects(
            RDF.type,
            CONSTRAINT_VOCAB.NormalizedConstraint,
        )
    )
    assert len(constraints) == 1
    return constraints[0]


def _governed_meaning(graph: Graph, constraint: URIRef) -> tuple:
    """Extract governed values without depending on the minted resource IRI."""

    governed_values = tuple(
        (
            str(predicate),
            tuple(
                sorted(
                    str(value)
                    for value in graph.objects(constraint, predicate)
                )
            ),
        )
        for predicate in GOVERNED_VALUE_PREDICATES
    )

    ordered_context = []
    for context_node in graph.objects(
        constraint,
        CONSTRAINT_VOCAB.hasSourceContext,
    ):
        order_values = list(
            graph.objects(
                context_node,
                CONSTRAINT_VOCAB.contextOrder,
            )
        )
        context_values = list(
            graph.objects(
                context_node,
                CONSTRAINT_VOCAB.contextValue,
            )
        )
        assert len(order_values) == 1
        assert len(context_values) == 1
        ordered_context.append(
            (
                int(order_values[0]),
                str(context_values[0]),
            )
        )

    provenance = tuple(
        sorted(
            str(source)
            for source in graph.objects(
                constraint,
                PROV.wasDerivedFrom,
            )
        )
    )

    return (
        governed_values,
        tuple(sorted(ordered_context)),
        provenance,
    )


def test_it_50_r2_s1_preserves_governed_meaning_independent_of_implementation(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """A different implementation IRI must not change the governed meaning."""

    first_output = tmp_path / "implementation-a.ttl"
    first_result = (
        constraint_normalization_agent.normalize_governed_constraint_to_file(
            governed_source=SOURCE_ROW,
            output_path=first_output,
        )
    )

    first_graph = Graph()
    first_graph.parse(first_output, format="turtle")
    first_constraint = _normalized_constraint(first_graph)

    alternate_namespace = Namespace(
        "https://example.invalid/alternate-implementation/constraint/"
    )
    monkeypatch.setattr(
        constraint_normalization_agent,
        "UADCON",
        alternate_namespace,
    )

    second_output = tmp_path / "implementation-b.ttl"
    second_result = (
        constraint_normalization_agent.normalize_governed_constraint_to_file(
            governed_source=SOURCE_ROW,
            output_path=second_output,
        )
    )

    second_graph = Graph()
    second_graph.parse(second_output, format="turtle")
    second_constraint = _normalized_constraint(second_graph)

    assert first_output.is_file()
    assert second_output.is_file()

    # The implementation-specific resource identifier may change.
    assert first_constraint != second_constraint

    # The governed identity and source meaning remain stable.
    assert _governed_meaning(
        first_graph,
        first_constraint,
    ) == _governed_meaning(
        second_graph,
        second_constraint,
    )
    assert first_graph.value(
        first_constraint,
        CONSTRAINT_VOCAB.governedUniqueId,
    ) == Literal("0100.0007")
    assert first_graph.value(
        first_constraint,
        CONSTRAINT_VOCAB.sourceRuleId,
    ) == Literal("UAD1001")
    assert first_graph.value(
        first_constraint,
        CONSTRAINT_VOCAB.requirementText,
    ) == Literal(SOURCE_ROW["requirement_text"])
    assert first_graph.value(
        first_constraint,
        CONSTRAINT_VOCAB.violationCondition,
    ) == Literal(SOURCE_ROW["violation_condition"])
    assert first_graph.value(
        first_constraint,
        PROV.wasDerivedFrom,
    ) == SOURCE_CONSTRAINT

    # The normalized representation contains no SHACL-specific terms.
    shacl_namespace = "http://www.w3.org/ns/shacl#"
    for graph in (first_graph, second_graph):
        for subject, predicate, obj in graph:
            for term in (subject, predicate, obj):
                if isinstance(term, URIRef):
                    assert not str(term).startswith(shacl_namespace)

    assert first_result.unique_id == "0100.0007"
    assert second_result.unique_id == "0100.0007"