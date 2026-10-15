"""IT-50R1S1 — produce normalized RDF from a governed source constraint."""

from __future__ import annotations

from importlib import import_module
from pathlib import Path

import pytest
from rdflib import Graph, Literal, Namespace, RDF, URIRef


CONSTRAINT_AGENT_MODULE = "app.services.constraint_normalization_agent"

CONSTRAINT = Namespace("https://dynamicontology.com/uad36/constraint/")
CONSTRAINT_VOCAB = Namespace(
    "https://dynamicontology.com/uad36/constraint-vocabulary#"
)
PROV = Namespace("http://www.w3.org/ns/prov#")

NORMALIZED_CONSTRAINT = URIRef(
    "https://dynamicontology.com/uad36/constraint/0100.0007"
)
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


def _normalization_file_writer():
    """Load the file-writing behavior required by IT-50R1S1."""

    try:
        module = import_module(CONSTRAINT_AGENT_MODULE)
    except ModuleNotFoundError as error:
        if error.name != CONSTRAINT_AGENT_MODULE:
            raise
        pytest.fail(
            "IT-50R1S1 requires "
            "app.services.constraint_normalization_agent before normalized "
            "constraint RDF can be written.",
            pytrace=False,
        )

    write_normalized_constraint = getattr(
        module,
        "normalize_governed_constraint_to_file",
        None,
    )
    assert callable(write_normalized_constraint), (
        "IT-50R1S1 requires "
        "normalize_governed_constraint_to_file("
        "governed_source, output_path) to write normalized RDF."
    )
    return write_normalized_constraint


def test_it_50_r1_s1_writes_traceable_normalized_constraint_rdf(
    tmp_path: Path,
) -> None:
    """Persist normalized RDF while preserving the governed source meaning."""

    normalize_to_file = _normalization_file_writer()
    output_path = tmp_path / "0100.0007.ttl"

    result = normalize_to_file(
        governed_source=SOURCE_ROW,
        output_path=output_path,
    )

    assert output_path.is_file(), (
        "IT-50R1S1 requires normalized constraint RDF to be written to the "
        f"requested governed output location: {output_path}"
    )

    graph = Graph()
    graph.parse(output_path, format="turtle")

    assert (
        NORMALIZED_CONSTRAINT,
        RDF.type,
        CONSTRAINT_VOCAB.NormalizedConstraint,
    ) in graph

    assert (
        NORMALIZED_CONSTRAINT,
        CONSTRAINT_VOCAB.governedUniqueId,
        Literal("0100.0007"),
    ) in graph

    assert (
        NORMALIZED_CONSTRAINT,
        CONSTRAINT_VOCAB.dataPointName,
        Literal("AddressLineText"),
    ) in graph

    assert (
        NORMALIZED_CONSTRAINT,
        CONSTRAINT_VOCAB.sourceRuleId,
        Literal("UAD1001"),
    ) in graph

    assert (
        NORMALIZED_CONSTRAINT,
        CONSTRAINT_VOCAB.requirementText,
        Literal(
            "Provide the address line for the subject property physical address."
        ),
    ) in graph

    assert (
        NORMALIZED_CONSTRAINT,
        CONSTRAINT_VOCAB.violationCondition,
        Literal("If AddressLineText is not provided"),
    ) in graph

    assert (
        NORMALIZED_CONSTRAINT,
        CONSTRAINT_VOCAB.severity,
        Literal("Fatal"),
    ) in graph

    assert (
        NORMALIZED_CONSTRAINT,
        CONSTRAINT_VOCAB.sourceLocator,
        Literal("data-constraints.csv#row=2"),
    ) in graph

    assert (
        NORMALIZED_CONSTRAINT,
        PROV.wasDerivedFrom,
        SOURCE_CONSTRAINT,
    ) in graph

    context_values = {
        str(value)
        for context_node in graph.objects(
            NORMALIZED_CONSTRAINT,
            CONSTRAINT_VOCAB.hasSourceContext,
        )
        for value in graph.objects(
            context_node,
            CONSTRAINT_VOCAB.contextValue,
        )
    }
    assert context_values == {
        "Subject",
        "Subject Property",
        "{No Subsection}",
        "Physical Address",
        "AddressLineText",
    }

    shacl_namespace = "http://www.w3.org/ns/shacl#"
    assert all(
        not str(predicate).startswith(shacl_namespace)
        for _, predicate, _ in graph
    ), "Normalized constraint RDF must not depend on SHACL representation."

    assert getattr(result, "unique_id", None) == "0100.0007"
    assert getattr(result, "data_point_name", None) == "AddressLineText"