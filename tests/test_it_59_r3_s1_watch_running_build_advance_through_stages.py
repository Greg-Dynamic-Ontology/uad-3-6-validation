"""IT-59R3S1: visualize persisted RDF as a running build advances.

Proposed UI contract:
* GET /constraint-workbench/runs/{run-directory-name} displays the run.
* Ordered elements identify iterations with data-pipeline-stage="IT-50", etc.
* The current worker has aria-current="step" and data-status="RUNNING".
* An SVG renders the latest available stage snapshot. Its edge elements expose
  data-rdf-subject, data-rdf-predicate and data-rdf-object as RDF term strings.
* A running page refreshes automatically (HTML refresh is sufficient here).
* CV.currentStage on the RUNNING run manifest identifies the active worker.

Only saved fixture knowledge is supplied. No workers are mocked as successful,
no real build is started, and viewing must not modify any saved run files.
"""

from hashlib import sha256
from html.parser import HTMLParser
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from rdflib import Graph, Literal, Namespace, RDF, URIRef
from rdflib.namespace import PROV

from app.main import app
from app.services.construction_exchange import UADEX, record_construction_stage_result

CFG = Namespace("https://dynamicontology.com/uad36/configuration#")
CV = Namespace("https://dynamicontology.com/uad36/constraint-vocabulary#")
ORDER = ("IT-50", "IT-51", "IT-52", "IT-53", "IT-54", "IT-55", "IT-56", "IT-58")


class _LivePage(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stages = []
        self.current = []
        self.run_ids = []
        self.edges = set()
        self.svg_depth = 0
        self.svg_count = 0
        self.refresh = False
        self.visible = []
        self.hidden_depth = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ("script", "style"):
            self.hidden_depth += 1
        if tag == "svg":
            self.svg_depth += 1
            self.svg_count += 1
        if "data-build-run-id" in attrs:
            self.run_ids.append(attrs["data-build-run-id"])
        if "data-pipeline-stage" in attrs:
            self.stages.append(attrs["data-pipeline-stage"])
            if attrs.get("aria-current") == "step":
                self.current.append((attrs["data-pipeline-stage"], attrs.get("data-status")))
        if self.svg_depth and all(key in attrs for key in (
            "data-rdf-subject", "data-rdf-predicate", "data-rdf-object",
        )):
            self.edges.add(tuple(attrs[key] for key in (
                "data-rdf-subject", "data-rdf-predicate", "data-rdf-object",
            )))
        if tag == "meta" and attrs.get("http-equiv", "").lower() == "refresh":
            content = attrs.get("content", "").split(";", 1)[0].strip()
            self.refresh = bool(content) and 0 < float(content) <= 5

    def handle_endtag(self, tag):
        if tag == "svg":
            self.svg_depth -= 1
        if tag in ("script", "style"):
            self.hidden_depth -= 1

    def handle_data(self, data):
        if not self.hidden_depth:
            self.visible.append(data)


def _snapshot_files(directory: Path):
    return {path.relative_to(directory): path.read_bytes()
            for path in directory.rglob("*") if path.is_file()}


def test_it_59_r3_s1_visualizes_actual_stage_rdf_and_current_running_stage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    ns = Namespace(f"urn:uad36:test:it59r3s1:{uuid4().hex}:")
    token = uuid4().hex
    run = URIRef(f"https://dynamicontology.com/uad36/construction/run/{token}")
    output_root = tmp_path / "build-runs"
    run_directory = output_root / token
    row_directory = run_directory / "constraints" / uuid4().hex
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
    configuration_bytes = configuration_path.read_bytes()
    monkeypatch.setattr(app.state, "configuration_file", configuration_path)

    manifest = Graph()
    batch = Graph()
    batch_path = run_directory / "batch-results.ttl"
    manifest_path = run_directory / "run.ttl"
    for triple in (
        (run, RDF.type, CV.ConstraintSetBuildRun),
        (run, RDF.type, PROV.Activity),
        (run, CV.selectedConstraintSet, ns.constraint_set),
        (run, CV.sourceVersion, Literal("test-release")),
        (run, CV.sourceWorkbook, ns.workbook),
        (run, CV.status, Literal("RUNNING")),
        (run, CV.batchResultsArtifact, URIRef(batch_path.as_uri())),
    ):
        manifest.add(triple)

    knowledge = Graph()
    knowledge.add((ns.constraint, RDF.type, CV.NormalizedConstraint))
    knowledge.add((ns.constraint, CV.governedUniqueId, Literal("0" + uuid4().hex)))
    knowledge.add((ns.constraint, CV.requirementText, Literal("Governed requirement " + uuid4().hex)))
    knowledge.add((ns.constraint, PROV.wasDerivedFrom, ns.source_row))

    def publish(stage: str, filename: str):
        record = record_construction_stage_result(
            output_graph=knowledge, constraint_id=str(ns.constraint),
            construction_stage=stage, construction_status="GREEN",
        )
        path = row_directory / filename
        knowledge.add((record.result_id, UADEX.rdfSnapshotPath, Literal(str(path))))
        knowledge.serialize(destination=path, format="turtle")
        for triple in knowledge:
            batch.add(triple)
        batch.set((record.result_id, UADEX.snapshotSha256,
                   Literal(sha256(path.read_bytes()).hexdigest())))
        batch.serialize(destination=batch_path, format="turtle")
        return Graph().parse(path, format="turtle")

    publish("normalized-constraint-representation", "01-normalized-constraint.ttl")
    knowledge.add((ns.constraint, CV.logicalSchemaResource, ns.named_schema_resource))
    latest = publish("logical-schema-binding", "02-logical-schema-binding.ttl")
    url = f"/constraint-workbench/runs/{token}"

    # Simulate the producer publishing progress between two operator refreshes.
    # Unique domain triples ensure a canned stage illustration cannot pass.
    for current_stage, current_iteration in (
        ("context-resolution", "IT-53"),
        ("validation-behavior", "IT-54"),
    ):
        manifest.set((run, CV.currentStage, Literal(current_stage)))
        manifest.serialize(destination=manifest_path, format="turtle")
        before_view = _snapshot_files(run_directory)
        with TestClient(app, follow_redirects=False) as client:
            response = client.get(url)
        assert response.status_code == 200, (
            "IT-59R3S1 requires an in-progress run visualization at "
            f"{url}; got HTTP {response.status_code}."
        )
        assert "text/html" in response.headers.get("content-type", "")
        page = _LivePage()
        page.feed(response.text)
        assert page.run_ids == [str(run)], "The visualization must identify this run."
        assert page.stages == list(ORDER), "Construction stages must appear in pipeline order."
        assert page.current == [(current_iteration, "RUNNING")], (
            "Exactly the active worker must be identified as currently processing."
        )
        assert page.refresh, "A running visualization must refresh to follow new stage results."
        assert page.svg_count >= 1, "Display an RDF graph, not only stage names or serialized text."
        assert page.edges == {tuple(str(term) for term in triple) for triple in latest}, (
            "Rendered RDF edges must represent the latest saved stage snapshot for this run."
        )
        assert str(ns.constraint) in " ".join(page.visible), "The actual governed constraint must be visible."
        assert _snapshot_files(run_directory) == before_view, "Viewing progress modified saved run knowledge."
        assert configuration_path.read_bytes() == configuration_bytes
        if current_stage == "context-resolution":
            knowledge.add((ns.constraint, CV.applicableContext, ns.context))
            knowledge.add((ns.context, CV.sourceContext, Literal("Context " + uuid4().hex)))
            latest = publish("context-resolution", "03-context-resolution.ttl")
