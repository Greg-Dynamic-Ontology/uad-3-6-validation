"""IT-59R3S2: inspect exactly the saved RDF for a selected run/stage result.

Proposed UI contract extends the existing run page:
* Stage-result links target that run page with ?result_id=<exchange result IRI>.
* data-selected-stage-result-id identifies the displayed saved result.
* The graph uses the existing SVG RDF-edge attributes.
* <pre id="stage-rdf"> exposes the original saved UTF-8 Turtle text.

Two runs each contain two constraints and two stage snapshots. Selection must
follow the exact result identity, not just the stage name or latest snapshot.
No other test modules are imported; all files are temporary pytest fixtures.
"""

from hashlib import sha256
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from rdflib import Graph, Literal, Namespace, RDF, URIRef
from rdflib.compare import isomorphic
from rdflib.namespace import PROV

from app.main import app
from app.services.construction_exchange import UADEX, record_construction_stage_result

CFG = Namespace("https://dynamicontology.com/uad36/configuration#")
CV = Namespace("https://dynamicontology.com/uad36/constraint-vocabulary#")
STAGES = ("normalized-constraint-representation", "logical-schema-binding")


class _InspectionPage(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []
        self.run_ids = []
        self.selected_results = []
        self.edges = set()
        self.svg_depth = 0
        self.rdf_blocks = []
        self._rdf_parts = None
        self.unescaped_source_markup = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a" and attrs.get("href"):
            self.links.append(attrs["href"])
        if "data-build-run-id" in attrs:
            self.run_ids.append(attrs["data-build-run-id"])
        if "data-selected-stage-result-id" in attrs:
            self.selected_results.append(attrs["data-selected-stage-result-id"])
        if tag == "svg":
            self.svg_depth += 1
        if self.svg_depth and all(key in attrs for key in (
                "data-rdf-subject", "data-rdf-predicate", "data-rdf-object",
        )):
            self.edges.add(tuple(attrs[key] for key in (
                "data-rdf-subject", "data-rdf-predicate", "data-rdf-object",
            )))
        if tag == "pre" and attrs.get("id") == "stage-rdf":
            self._rdf_parts = []
        if tag == "governed-note":
            self.unescaped_source_markup = True

    def handle_data(self, data):
        if self._rdf_parts is not None:
            self._rdf_parts.append(data)

    def handle_endtag(self, tag):
        if tag == "svg":
            self.svg_depth -= 1
        if tag == "pre" and self._rdf_parts is not None:
            self.rdf_blocks.append(''.join(self._rdf_parts))
            self._rdf_parts = None


def _files(directory: Path):
    return {path.relative_to(directory): path.read_bytes()
            for path in directory.rglob("*") if path.is_file()}


@pytest.mark.parametrize("stage_index", [0, 1], ids=["normalization", "logical-schema-binding"])
def test_it_59_r3_s2_inspects_exact_saved_rdf_for_selected_run_and_stage_result(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stage_index: int,
) -> None:
    ns = Namespace(f"urn:uad36:test:it59r3s2:{uuid4().hex}:")
    output_root = tmp_path / "build-runs"
    configuration = Graph()
    for triple in (
            (ns.configuration, RDF.type, CFG.ApplicationConfiguration),
            (ns.configuration, CFG.usesConstraintBuildProfile, ns.profile),
            (ns.profile, RDF.type, CFG.ConstraintBuildProfile),
            (ns.profile, CFG.buildOutputDirectory, Literal(str(output_root))),
    ):
        configuration.add(triple)
    configuration_path = tmp_path / "configuration.ttl"
    configuration.serialize(destination=configuration_path, format="turtle")
    monkeypatch.setattr(app.state, "configuration_file", configuration_path)
    runs = []
    for run_index in range(2):
        token = uuid4().hex
        run = URIRef(f"https://dynamicontology.com/uad36/construction/run/{token}")
        directory = output_root / token
        directory.mkdir(parents=True)
        batch = Graph()
        results = {}
        for row_index in range(2):
            constraint = URIRef(f"{ns}constraint-{row_index}")
            row_directory = directory / "constraints" / uuid4().hex
            row_directory.mkdir(parents=True)
            knowledge = Graph()
            knowledge.bind("cv", CV)
            knowledge.add((constraint, RDF.type, CV.NormalizedConstraint))
            knowledge.add((constraint, CV.governedUniqueId, Literal("0" + uuid4().hex)))
            knowledge.add((constraint, PROV.wasDerivedFrom, ns.source_row))
            for index, stage in enumerate(STAGES):
                if index:
                    knowledge.add((constraint, CV.logicalSchemaResource, ns.schema_resource))
                # HTML-like source text must remain text in the Turtle display.
                marker = f"<governed-note>{uuid4().hex} & governed text</governed-note>"
                knowledge.add((constraint, CV.requirementText, Literal(marker)))
                record = record_construction_stage_result(
                    output_graph=knowledge, constraint_id=str(constraint),
                    construction_stage=stage, construction_status="GREEN",
                )
                snapshot_path = row_directory / f"{index + 1:02d}-{stage}.ttl"
                knowledge.add((record.result_id, UADEX.rdfSnapshotPath, Literal(str(snapshot_path))))
                # Preserve comments and formatting to distinguish an exact saved
                # serialization from a semantically equivalent reserialization.
                turtle = (
                        f"# Original snapshot: run {run_index}, row {row_index}, stage {index}\n\n"
                        + knowledge.serialize(format="turtle")
                        + f"\n# End original snapshot {uuid4().hex}\n"
                )
                snapshot_path.write_bytes(turtle.encode("utf-8"))
                for triple in knowledge:
                    batch.add(triple)
                batch.set((record.result_id, UADEX.snapshotSha256,
                           Literal(sha256(snapshot_path.read_bytes()).hexdigest())))
                results[row_index, index] = (record.result_id, snapshot_path, turtle)
        batch_path = directory / "batch-results.ttl"
        batch.serialize(destination=batch_path, format="turtle")
        manifest = Graph()
        for triple in (
                (run, RDF.type, CV.ConstraintSetBuildRun),
                (run, RDF.type, PROV.Activity),
                (run, CV.selectedConstraintSet, ns.constraint_set),
                (run, CV.sourceVersion, Literal("test-release")),
                (run, CV.sourceWorkbook, ns.workbook),
                (run, CV.status, Literal("COMPLETE")),
                (run, CV.batchResultsArtifact, URIRef(batch_path.as_uri())),
        ):
            manifest.add(triple)
        manifest.serialize(destination=directory / "run.ttl", format="turtle")
        runs.append((token, run, results))

    token, run, results = runs[0]
    selected_result, snapshot_path, expected_turtle = results[0, stage_index]
    url = f"/constraint-workbench/runs/{token}"
    original_files = _files(tmp_path)
    with TestClient(app, follow_redirects=False) as client:
        response = client.get(url)
        assert response.status_code == 200
        page = _InspectionPage()
        page.feed(response.text)
        links = []
        for href in page.links:
            parsed = urlsplit(href)
            if (not parsed.scheme and not parsed.netloc and parsed.path == url
                    and parse_qs(parsed.query).get("result_id") == [str(selected_result)]):
                links.append(href)
        assert links, (
            "IT-59R3S2 requires an operator-selectable link for each saved stage result, "
            "identifying its exact exchange result IRI within the selected run."
        )
        inspected = client.get(links[0])
    assert inspected.status_code == 200
    assert "text/html" in inspected.headers.get("content-type", "")
    page = _InspectionPage()
    page.feed(inspected.text)
    assert page.run_ids == [str(run)]
    assert page.selected_results == [str(selected_result)], (
        "The displayed result must be explicitly identified as the selected stage result."
    )
    expected_graph = Graph().parse(snapshot_path, format="turtle")
    assert page.edges == {tuple(str(term) for term in triple) for triple in expected_graph}, (
        "The selected graph must match this run's exact saved stage snapshot, "
        "not a later stage, another row, or another run."
    )
    assert page.rdf_blocks == [expected_turtle], (
        "Show the original serialized Turtle exactly, including comments and whitespace."
    )
    assert not page.unescaped_source_markup, "Governed RDF text must be HTML-escaped."
    assert isomorphic(Graph().parse(data=page.rdf_blocks[0], format="turtle"), expected_graph)
    assert _files(tmp_path) == original_files, "Inspecting a stage modified saved source or run artifacts."
