"""IT-52R1S1: bind a normalized constraint to a matching Logical Schema resource."""

from __future__ import annotations

import csv
import os
from importlib import import_module
from pathlib import Path
from typing import Any

import pytest
from rdflib import Graph, Namespace, RDF, URIRef


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_CSV = PROJECT_ROOT / "data" / "data-constraints.csv"

CONSTRAINT_AGENT_MODULE = "app.services.constraint_normalization_agent"
BINDING_AGENT_MODULE = "app.services.logical_schema_binding_agent"

CONSTRAINT_VOCAB = Namespace(
    "https://dynamicontology.com/uad36/constraint-vocabulary#"
)
LOGICAL_SCHEMA = Namespace(
    "https://dynamicontology.com/uad36/logical-schema#"
)
LOGICAL_SCHEMA_MODEL_IRI = URIRef(
    "https://dynamicontology.com/uad36/logical-schema/model"
)

REQUIRED_SOURCE_COLUMNS = (
    "Unique ID",
    "Data Point Name / Value",
    "Message ID",
    "Message Text",
    "Rule Logic",
    "Severity",
)

CONTEXT_SOURCE_COLUMNS = (
    "Property Affected",
    "Report Section",
    "Report Subsection",
    "Report Label / Value",
    "Data Point Name / Value",
)

SKIPPED_DIRECTORY_NAMES = {
    ".git",
    ".venv",
    "__pycache__",
    "chatgpt-sources",
    "node_modules",
    "output",
    "ready_to_copy",
    "tmp",
    "venv",
}


def _find_logical_schema_graph() -> Graph:
    """Find the serialized canonical model by its governed RDF identity."""
    assert PROJECT_ROOT.is_dir(), (
        f"Could not resolve project root from this test: {PROJECT_ROOT}"
    )

    model_graphs: list[tuple[Path, Graph]] = []

    for current_directory, directory_names, file_names in os.walk(
        PROJECT_ROOT
    ):
        directory_names[:] = [
            name
            for name in directory_names
            if name not in SKIPPED_DIRECTORY_NAMES
        ]

        for file_name in file_names:
            if not file_name.lower().endswith(".ttl"):
                continue

            turtle_path = Path(current_directory) / file_name
            candidate_graph = Graph()

            try:
                candidate_graph.parse(turtle_path, format="turtle")
            except Exception:
                # Other Turtle files in the repository are not necessarily
                # Logical Schema artifacts. Ignore files that cannot be read
                # as Turtle and continue looking for the governed model IRI.
                continue

            if (
                LOGICAL_SCHEMA_MODEL_IRI,
                RDF.type,
                LOGICAL_SCHEMA.SchemaModel,
            ) in candidate_graph:
                model_graphs.append((turtle_path, candidate_graph))

    assert model_graphs, (
        "IT-52R1S1 could not find a serialized Logical Schema Model. "
        "A Turtle file must identify "
        "<https://dynamicontology.com/uad36/logical-schema/model> "
        "as an lsm:SchemaModel."
    )

    # If the project keeps identical copies of the canonical graph, any copy
    # has the same governed content. If different model graphs are present,
    # select the graph with the most triples so a partial serialization is
    # not mistaken for the complete model.
    return max(
        model_graphs,
        key=lambda item: len(item[1]),
    )[1]


def _element_resources_by_local_name(
    logical_schema_graph: Graph,
) -> dict[str, set[URIRef]]:
    """Index governed element declarations by their schema QName local name."""
    resources_by_name: dict[str, set[URIRef]] = {}

    for declaration in logical_schema_graph.subjects(
        RDF.type,
        LOGICAL_SCHEMA.ElementDeclaration,
    ):
        if not isinstance(declaration, URIRef):
            continue

        for qname_predicate in (
            LOGICAL_SCHEMA.name,
            LOGICAL_SCHEMA.ref,
        ):
            for qname in logical_schema_graph.objects(
                declaration,
                qname_predicate,
            ):
                if not isinstance(qname, URIRef):
                    continue

                for local_name in logical_schema_graph.objects(
                    qname,
                    LOGICAL_SCHEMA.local_name,
                ):
                    name = str(local_name).strip()
                    if name:
                        resources_by_name.setdefault(name, set()).add(
                            declaration
                        )

    return resources_by_name


def _governed_source_rows_with_one_schema_match(
    element_resources: dict[str, set[URIRef]],
) -> list[dict[str, Any]]:
    """Prepare governed rows whose data point has one schema match."""
    assert SOURCE_CSV.is_file(), (
        "The governed source CSV is required for IT-52R1S1: "
        f"{SOURCE_CSV}"
    )

    prepared_rows: list[dict[str, Any]] = []

    with SOURCE_CSV.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as source_file:
        reader = csv.DictReader(source_file)

        assert reader.fieldnames is not None, (
            f"The governed source CSV has no header row: {SOURCE_CSV}"
        )

        missing_columns = set(REQUIRED_SOURCE_COLUMNS) - set(reader.fieldnames)
        assert not missing_columns, (
            "The governed source CSV is missing required columns: "
            f"{sorted(missing_columns)}"
        )

        for record_number, csv_row in enumerate(reader, start=2):
            if any(
                not (csv_row.get(column) or "").strip()
                for column in REQUIRED_SOURCE_COLUMNS
            ):
                continue

            data_point_name = (
                csv_row["Data Point Name / Value"].strip()
            )
            matching_resources = element_resources.get(
                data_point_name,
                set(),
            )

            # This scenario covers a single unambiguous schema resource.
            # Unmatched or ambiguous cases belong to separate scenarios.
            if len(matching_resources) != 1:
                continue

            source_locator = f"data-constraints.csv#row={record_number}"
            context_fields = [
                (csv_row.get(column) or "").strip()
                for column in CONTEXT_SOURCE_COLUMNS
                if (csv_row.get(column) or "").strip()
            ]

            prepared_rows.append(
                {
                    "unique_id": csv_row["Unique ID"].strip(),
                    "data_point_name": data_point_name,
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
                    "_caller_record_number": record_number,
                    "_expected_schema_resource": next(
                        iter(matching_resources)
                    ),
                }
            )

    assert prepared_rows, (
        "The governed CSV and Logical Schema Model must contain at least "
        "one sufficient source row whose data point matches exactly one "
        "Logical Schema element declaration."
    )
    return prepared_rows


_LOGICAL_SCHEMA_GRAPH = _find_logical_schema_graph()
_ELEMENT_RESOURCES = _element_resources_by_local_name(
    _LOGICAL_SCHEMA_GRAPH
)
GOVERNED_SOURCE_ROWS = _governed_source_rows_with_one_schema_match(
    _ELEMENT_RESOURCES
)


def _load_normalizer():
    """Load IT-50 production behavior to create normalized RDF input."""
    try:
        module = import_module(CONSTRAINT_AGENT_MODULE)
    except ModuleNotFoundError as error:
        if error.name != CONSTRAINT_AGENT_MODULE:
            raise
        pytest.fail(
            "IT-52R1S1 requires the IT-50 normalization agent to produce "
            "the normalized constraint RDF used as binding input.",
            pytrace=False,
        )

    normalize_to_file = getattr(
        module,
        "normalize_governed_constraint_to_file",
        None,
    )
    assert callable(normalize_to_file), (
        "IT-52R1S1 requires the IT-50 contract "
        "normalize_governed_constraint_to_file("
        "governed_source, output_path)."
    )
    return normalize_to_file


def _load_binding_operation():
    """Load the production operation that binds normalized RDF to the model."""
    try:
        module = import_module(BINDING_AGENT_MODULE)
    except ModuleNotFoundError as error:
        if error.name != BINDING_AGENT_MODULE:
            raise
        pytest.fail(
            "IT-52R1S1 requires "
            "app.services.logical_schema_binding_agent before normalized "
            "constraint RDF can be bound to the Logical Schema Model.",
            pytrace=False,
        )

    bind_constraint = getattr(
        module,
        "bind_normalized_constraint_to_logical_schema",
        None,
    )
    assert callable(bind_constraint), (
        "IT-52R1S1 requires "
        "bind_normalized_constraint_to_logical_schema("
        "normalized_graph, logical_schema_graph, constraint_id, "
        "output_graph) to add governed Logical Schema bindings."
    )
    return bind_constraint


@pytest.mark.parametrize(
    "governed_source",
    GOVERNED_SOURCE_ROWS,
    ids=[
        f"source-row-{row['_caller_record_number']}"
        for row in GOVERNED_SOURCE_ROWS
    ],
)
def test_it_52_r1_s1_binds_normalized_constraint_to_one_matching_logical_schema_resource(
    governed_source: dict[str, Any],
    tmp_path: Path,
) -> None:
    """Bind each selected normalized row to its exact schema resource IRI."""
    normalize_to_file = _load_normalizer()
    bind_constraint = _load_binding_operation()

    record_number = governed_source["_caller_record_number"]
    normalized_path = tmp_path / f"normalized-row-{record_number}.ttl"

    normalization_result = normalize_to_file(
        governed_source=governed_source,
        output_path=normalized_path,
    )

    assert normalized_path.is_file(), (
        "IT-50 must write the normalized RDF input to the requested path: "
        f"{normalized_path}"
    )

    normalized_graph = Graph()
    normalized_graph.parse(normalized_path, format="turtle")

    constraint = URIRef(normalization_result.constraint_id)
    assert (
        constraint,
        RDF.type,
        CONSTRAINT_VOCAB.NormalizedConstraint,
    ) in normalized_graph, (
        "The binding input must identify the normalized constraint "
        "resource produced by IT-50."
    )

    bound_graph = Graph()
    bind_constraint(
        normalized_graph=normalized_graph,
        logical_schema_graph=_LOGICAL_SCHEMA_GRAPH,
        constraint_id=str(constraint),
        output_graph=bound_graph,
    )

    expected_schema_resource = governed_source[
        "_expected_schema_resource"
    ]

    assert (
        constraint,
        CONSTRAINT_VOCAB.boundLogicalSchemaResource,
        expected_schema_resource,
    ) in bound_graph, (
        "IT-52 must bind the normalized constraint to the exact governed "
        "Logical Schema resource IRI, not mint or infer a replacement IRI."
    )

    actual_bindings = set(
        bound_graph.objects(
            constraint,
            CONSTRAINT_VOCAB.boundLogicalSchemaResource,
        )
    )
    assert actual_bindings == {expected_schema_resource}, (
        "A normalized constraint with one matching Logical Schema resource "
        "must have exactly that one schema binding."
    )

    assert set(normalized_graph).issubset(set(bound_graph)), (
        "Binding must preserve the normalized constraint knowledge."
    )