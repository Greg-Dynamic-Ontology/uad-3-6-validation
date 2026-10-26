"""IT-61R2S2: a partial run lists only verified completed-stage RDF results.

Use the existing run-page timeline and data-visualization-action="select"
links. Follow each link and compare its displayed graph with that stage's
actual snapshot. A pending stage, including one with explicitly unverified
output, must not appear among selectable completed results.

All fixture IDs are generated and helpers are local. No worker is executed or
mocked; this scenario inspects persisted in-progress production state.
"""

from hashlib import sha256
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from rdflib import Graph, Literal, Namespace, RDF, URIRef
from rdflib.namespace import PROV

from app.main import app
from app.services.construction_exchange import UADEX, record_construction_stage_result

CFG = Namespace("https://dynamicontology.com/uad36/configuration#")
CV = Namespace("https://dynamicontology.com/uad36/constraint-vocabulary#")
STAGES = (
    ("IT-50", "normalized-constraint-representation"),
    ("IT-52", "logical-schema-binding"),
    ("IT-53", "context-resolution"),
    ("IT-54", "validation-behavior"),
    ("IT-55", "instance-rdf-binding"),
    ("IT-56", "shacl-representation"),
)


class _TimelinePage(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.choices = []
        self.selected = []
        self.run_ids = []
        self.edges = set()
        self.stages = []
        self._choice = None
        self._svg_depth = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a" and attrs.get("data-visualization-action") == "select":
            self._choice = {"href": attrs.get("href", ""), "text": []}
        if "data-selected-stage-result-id" in attrs:
            self.selected.append(attrs["data-selected-stage-result-id"])
        if "data-build-run-id" in attrs:
            self.run_ids.append(attrs["data-build-run-id"])
        if "data-pipeline-stage" in attrs:
            self.stages.append((attrs["data-pipeline-stage"], attrs.get("data-status")))
        if tag == "svg":
            self._svg_depth += 1
        if self._svg_depth and all(key in attrs for key in (
            "data-rdf-subject", "data-rdf-predicate", "data-rdf-object",
        )):
            self.edges.add(tuple(attrs[key] for key in (
                "data-rdf-subject", "data-rdf-predicate", "data-rdf-object",
            )))

    def handle_data(self, data):
        if self._choice is not None:
            self._choice["text"].append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._choice is not None:
            self.choices.append(self._choice)
            self._choice = None
        if tag == "svg":
            self._svg_depth -= 1


def _files(directory):
    return {path.relative_to(directory): path.read_bytes()
            for path in directory.rglob("*") if path.is_file()}


@pytest.mark.parametrize("completed_count, has_unverified_output", [
    (1, False), (3, False), (2, True),
], ids=["one-completed-stage", "three-completed-stages", "unfinished-stage-has-unverified-output"])
def test_it_61_r2_s2_lists_only_completed_stage_results_in_execution_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    completed_count: int, has_unverified_output: bool,
) -> None:
    ns = Namespace(f"urn:uad36:test:it61r2s2:{uuid4().hex}:")
    token = uuid4().hex
    run = URIRef(f"https://dynamicontology.com/uad36/construction/run/{token}")
    output_root = tmp_path / "build-runs"
    directory = output_root / token
    row_directory = directory / "constraints" / uuid4().hex
    row_directory.mkdir(parents=True)
    configuration_path = tmp_path / "configuration.ttl"
    configuration = Graph()
    for triple in (
        (ns.configuration, RDF.type, CFG.ApplicationConfiguration),
        (ns.configuration, CFG.usesConstraintBuildProfile, ns.profile),
        (ns.profile, RDF.type, CFG.ConstraintBuildProfile),
        (ns.profile, CFG.buildOutputDirectory, Literal(str(output_root))),
    ):
        configuration.add(triple)
    configuration.serialize(destination=configuration_path, format="turtle")
    monkeypatch.setattr(app.state, "configuration_file", configuration_path)
    batch = Graph()
    knowledge = Graph()
    knowledge.add((ns.constraint, RDF.type, CV.NormalizedConstraint))
    knowledge.add((ns.constraint, CV.governedUniqueId, Literal("0" + uuid4().hex)))
    knowledge.add((ns.constraint, PROV.wasDerivedFrom, ns.source_row))
    snapshots = []

    def save_stage(index, verified):
        record = record_construction_stage_result(
            output_graph=knowledge, constraint_id=str(ns.constraint),
            construction_stage=STAGES[index][1], construction_status="GREEN",
        )
        knowledge.add((record.result_id, UADEX.availableForDownstream, Literal(verified)))
        knowledge.add((ns.constraint, ns[f"stageKnowledge-{index}"], Literal(uuid4().hex)))
        path = row_directory / f"{index + 1:02d}-{STAGES[index][1]}.ttl"
        knowledge.add((record.result_id, UADEX.rdfSnapshotPath, Literal(str(path))))
        knowledge.serialize(destination=path, format="turtle")
        for triple in knowledge:
            batch.add(triple)
        batch.set((record.result_id, UADEX.snapshotSha256, Literal(sha256(path.read_bytes()).hexdigest())))
        return record.result_id, path

    for index in range(completed_count):
        snapshots.append(save_stage(index, True))
    unverified = save_stage(completed_count, False) if has_unverified_output else None
    batch_path = directory / "batch-results.ttl"
    batch.serialize(destination=batch_path, format="turtle")
    manifest = Graph()
    for triple in (
        (run, RDF.type, CV.ConstraintPipelineRun),
        (run, RDF.type, PROV.Activity),
        (run, CV.sourceWorkbook, ns.workbook),
        (run, CV.sourceWorksheet, Literal("GovernedRules")),
        (run, CV.governedUniqueId, next(knowledge.objects(ns.constraint, CV.governedUniqueId))),
        (run, CV.totalRowCount, Literal(1)),
        (run, CV.status, Literal("RUNNING")),
        (run, CV.currentStage, Literal(STAGES[completed_count][1])),
        (run, CV.batchResultsArtifact, URIRef(batch_path.as_uri())),
    ):
        manifest.add(triple)
    manifest.serialize(destination=directory / "run.ttl", format="turtle")
    originals = _files(tmp_path)
    url = f"/constraint-workbench/runs/{token}"
    with TestClient(app, follow_redirects=False) as client:
        response = client.get(url, params={"playback": "paused"})
        assert response.status_code == 200
        page = _TimelinePage()
        page.feed(response.text)
        assert page.run_ids == [str(run)]
        offered_ids = []
        for choice in page.choices:
            parsed = urlsplit(choice["href"])
            assert not parsed.scheme and not parsed.netloc and parsed.path == url
            ids = parse_qs(parsed.query).get("result_id", [])
            assert len(ids) == 1
            offered_ids.append(ids[0])
        assert offered_ids == [str(result) for result, _ in snapshots], (
            "IT-61R2S2 requires exactly the completed verified stage results, in execution order. "
            "An unfinished or explicitly unverified stage must not be offered as produced output."
        )
        for index, (choice, (result, path)) in enumerate(zip(page.choices, snapshots)):
            assert STAGES[index][0] in " ".join(choice["text"])
            inspected = client.get(choice["href"])
            assert inspected.status_code == 200
            result_page = _TimelinePage()
            result_page.feed(inspected.text)
            assert result_page.run_ids == [str(run)]
            assert result_page.selected == [str(result)]
            snapshot = Graph().parse(path, format="turtle")
            assert result_page.edges == {tuple(str(term) for term in triple) for triple in snapshot}
        if unverified is not None:
            # A manually supplied result IRI must not bypass the timeline gate.
            rejected = client.get(url, params={"result_id": str(unverified[0]), "playback": "paused"})
            assert rejected.status_code in (400, 404, 409), "Unverified output must not be opened as a completed stage result."
    assert _files(tmp_path) == originals, "Opening a timeline must not create, regenerate or modify stage results."
