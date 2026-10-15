"""IT-50R5S2 — produce normalized RDF from a governed CSV row."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from rdflib import Graph, Literal, Namespace, RDF, URIRef

from app.services.constraint_normalization_agent import (
    normalize_governed_constraint_to_file,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_CSV = PROJECT_ROOT / "data" / "data-constraints.csv"

CONSTRAINT_VOCAB = Namespace(
    "https://dynamicontology.com/uad36/constraint-vocabulary#"
)
PROV = Namespace("http://www.w3.org/ns/prov#")

REQUIRED_COLUMNS = (
    "Unique ID",
    "Data Point Name / Value",
    "Message ID",
    "Message Text",
    "Rule Logic",
    "Severity",
)


def _governed_source_from_csv() -> dict[str, Any]:
    """Materialize one sufficient row from the authoritative CSV."""

    assert SOURCE_CSV.is_file(), (
        "The authoritative governed source CSV is required for IT-50R5S2: "
        f"{SOURCE_CSV}"
    )

    with SOURCE_CSV.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as source_file:
        reader = csv.DictReader(source_file)

        assert reader.fieldnames is not None, (
            f"The governed source CSV has no header row: {SOURCE_CSV}"
        )

        missing_columns = set(REQUIRED_COLUMNS) - set(reader.fieldnames)
        assert not missing_columns, (
            "The governed source CSV is missing required columns: "
            f"{sorted(missing_columns)}"
        )

        for record_number, csv_row in enumerate(reader, start=2):
            if any(
                not (csv_row.get(column) or "").strip()
                for column in REQUIRED_COLUMNS
            ):
                continue

            source_locator = f"data-constraints.csv#row={record_number}"
            context_columns = (
                "Property Affected",
                "Report Section",
                "Report Subsection",
                "Report Label / Value",
                "Data Point Name / Value",
            )
            context_fields = [
                (csv_row.get(column) or "").strip()
                for column in context_columns
                if (csv_row.get(column) or "").strip()
            ]

            return {
                "unique_id": csv_row["Unique ID"].strip(),
                "data_point_name": (
                    csv_row["Data Point Name / Value"].strip()
                ),
                "source_rule_id": csv_row["Message ID"].strip(),
                "requirement_text": csv_row["Message Text"].strip(),
                "violation_condition": csv_row["Rule Logic"].strip(),
                "severity": csv_row["Severity"].strip(),
                "context_fields": context_fields,
                "source_locator": source_locator,
                "source_constraint_uri": (
                    "urn:uad36:governed-source:"
                    f"{source_locator}"
                ),
            }

    raise AssertionError(
        "The governed source CSV has no row with sufficient knowledge "
        "for IT-50R5S2."
    )


def test_it_50_r5_s2_produces_normalized_rdf_from_governed_csv_row(
    tmp_path: Path,
) -> None:
    """Write traceable normalized RDF from an actual governed CSV row."""

    governed_source = _governed_source_from_csv()
    output_path = tmp_path / "normalized-governed-row.ttl"

    result = normalize_governed_constraint_to_file(
        governed_source=governed_source,
        output_path=output_path,
    )

    assert output_path.is_file(), (
        "The normalized RDF must be written by the production normalizer "
        f"to the requested path: {output_path}"
    )

    output_graph = Graph()
    output_graph.parse(output_path, format="turtle")
    normalized_constraint = URIRef(result.constraint_id)

    assert (
        normalized_constraint,
        RDF.type,
        CONSTRAINT_VOCAB.NormalizedConstraint,
    ) in output_graph

    expected_values = (
        ("governedUniqueId", governed_source["unique_id"]),
        ("dataPointName", governed_source["data_point_name"]),
        ("sourceRuleId", governed_source["source_rule_id"]),
        ("requirementText", governed_source["requirement_text"]),
        ("violationCondition", governed_source["violation_condition"]),
        ("severity", governed_source["severity"]),
        ("sourceLocator", governed_source["source_locator"]),
    )

    for predicate_name, expected_value in expected_values:
        assert (
            normalized_constraint,
            getattr(CONSTRAINT_VOCAB, predicate_name),
            Literal(expected_value),
        ) in output_graph

    assert (
        normalized_constraint,
        PROV.wasDerivedFrom,
        URIRef(governed_source["source_constraint_uri"]),
    ) in output_graph

    actual_context = sorted(
        (
            int(order),
            str(value),
        )
        for context_node in output_graph.objects(
            normalized_constraint,
            CONSTRAINT_VOCAB.hasSourceContext,
        )
        for order in output_graph.objects(
            context_node,
            CONSTRAINT_VOCAB.contextOrder,
        )
        for value in output_graph.objects(
            context_node,
            CONSTRAINT_VOCAB.contextValue,
        )
    )
    expected_context = [
        (index, value)
        for index, value in enumerate(
            governed_source["context_fields"],
            start=1,
        )
    ]
    assert actual_context == expected_context

    assert result.unique_id == governed_source["unique_id"]
    assert result.data_point_name == governed_source["data_point_name"]
    assert result.source_rule_id == governed_source["source_rule_id"]

    shacl_namespace = "http://www.w3.org/ns/shacl#"
    assert all(
        not str(predicate).startswith(shacl_namespace)
        for _, predicate, _ in output_graph
    ), "Normalized constraint RDF must not depend on a SHACL representation."