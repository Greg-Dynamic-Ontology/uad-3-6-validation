"""IT-50R6S2: record a RED normalization result as governed RDF."""

from __future__ import annotations

import csv
import importlib
import uuid
from pathlib import Path

from rdflib import Graph, Literal, RDF, URIRef


PROJECT_ROOT = Path(__file__).resolve().parents[1]
GOVERNED_CSV = PROJECT_ROOT / "data" / "data-constraints.csv"
SCENARIO_ID = "IT-50R6S2"
REQUIRED_SOURCE_COLUMNS = (
    "Unique ID",
    "Primary Data Element",
    "Message ID",
    "Message Text",
    "Rule Logic",
    "Severity",
)


def _local_name(term: object) -> str:
    text = str(term)
    return text.rsplit("#", 1)[-1].rsplit("/", 1)[-1].rsplit(":", 1)[-1]


def _read_governed_constraint_id() -> str:
    assert GOVERNED_CSV.is_file(), (
        f"The governed source CSV is missing: {GOVERNED_CSV}"
    )

    with GOVERNED_CSV.open("r", encoding="utf-8-sig", newline="") as source_file:
        reader = csv.DictReader(source_file)
        assert reader.fieldnames is not None, "The governed source CSV has no header."

        for row in reader:
            if all((row.get(column) or "").strip() for column in REQUIRED_SOURCE_COLUMNS):
                return row["Unique ID"].strip()

    raise AssertionError(
        "The governed source CSV has no row populated with the required "
        "normalization knowledge."
    )


def _objects_for_local_predicate(
    graph: Graph,
    subject: URIRef,
    predicate_local_name: str,
) -> list[object]:
    return [
        value
        for predicate, value in graph.predicate_objects(subject)
        if _local_name(predicate) == predicate_local_name
    ]


def test_it_50_r6_s2_records_a_red_normalization_test_result(
    tmp_path: Path,
) -> None:
    constraint_id = _read_governed_constraint_id()
    source_artifact_uri = GOVERNED_CSV.resolve().as_uri()
    execution_activity_uri = f"urn:uad36:test-execution:{uuid.uuid4()}"

    normalization_agent = importlib.import_module(
        "app.services.constraint_normalization_agent"
    )
    recorder = getattr(
        normalization_agent,
        "record_normalization_test_result",
        None,
    )
    assert callable(recorder), (
        "The normalization agent must record completed test results as "
        "governed construction RDF."
    )

    result_path = tmp_path / "normalization-test-results.ttl"
    recorder(
        output_path=result_path,
        scenario_id=SCENARIO_ID,
        status="RED",
        execution_activity_uri=execution_activity_uri,
        tested_constraint_id=constraint_id,
        source_artifact_uris=[source_artifact_uri],
    )

    assert result_path.is_file(), (
        "Recording a normalization result must produce its RDF artifact "
        "at the caller-configured output path."
    )

    graph = Graph()
    graph.parse(result_path, format="turtle")

    result_resources = {
        subject
        for subject, _, result_type in graph.triples((None, RDF.type, None))
        if _local_name(result_type) == "GovernedTestResult"
    }
    assert result_resources, (
        "The RDF artifact must contain a governed test-result resource."
    )

    result = next(iter(result_resources))

    scenario_values = _objects_for_local_predicate(graph, result, "scenarioId")
    assert any(str(value) == SCENARIO_ID for value in scenario_values), (
        "The governed test-result resource must identify its scenario."
    )

    status_values = _objects_for_local_predicate(graph, result, "status")
    assert any(str(value) == "RED" for value in status_values), (
        "The governed test-result resource must record RED status."
    )
    assert not any(str(value) == "GREEN" for value in status_values), (
        "A RED result must not also be recorded as GREEN."
    )

    tested_constraint_values = _objects_for_local_predicate(
        graph,
        result,
        "testedConstraintId",
    )
    assert any(str(value) == constraint_id for value in tested_constraint_values), (
        "The governed test-result resource must identify the tested constraint."
    )

    execution_values = _objects_for_local_predicate(
        graph,
        result,
        "wasGeneratedBy",
    )
    assert URIRef(execution_activity_uri) in execution_values, (
        "The governed test-result resource must link to its test execution activity."
    )

    source_artifact_values = _objects_for_local_predicate(
        graph,
        result,
        "usedSourceArtifact",
    )
    assert URIRef(source_artifact_uri) in source_artifact_values, (
        "The governed test-result resource must link to the source artifact used."
    )