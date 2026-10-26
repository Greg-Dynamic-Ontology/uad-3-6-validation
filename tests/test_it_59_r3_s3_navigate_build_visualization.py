"""IT-59R3S3: navigate saved stage RDF without changing run artifacts.

Proposed server-rendered control contract:
* playback=playing or playback=paused in the run-page query.
* One data-playback-state attribute reports the selected playback state.
* Links expose data-visualization-action values pause, resume, previous, next,
  or select. Stage selection and playback mode are preserved in their URLs.
* Playing refreshes automatically; paused pages do not automatically advance.
* Previous/next are absent or disabled at the respective boundaries.

This test follows actual rendered links through HTTP, verifying each displayed
snapshot. It does not import helpers or test functions from other test modules.
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
    "normalized-constraint-representation", "logical-schema-binding", "context-resolution",
)


class _NavigationPage(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.controls = {}
        self.states = []
        self.selected = []
        self.run_ids = []
        self.refresh = False
        self.advance_url = None
        self.edges = set()
        self.svg_depth = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        action = attrs.get("data-visualization-action")
        if action and tag == "a" and attrs.get("href") and attrs.get("aria-disabled") != "true":
            self.controls.setdefault(action, []).append(attrs["href"])
        if "data-playback-state" in attrs:
            self.states.append(attrs["data-playback-state"])
        if "data-selected-stage-result-id" in attrs:
            self.selected.append(attrs["data-selected-stage-result-id"])
        if "data-build-run-id" in attrs:
            self.run_ids.append(attrs["data-build-run-id"])
        if tag == "meta" and attrs.get("http-equiv", "").lower() == "refresh":
            self.refresh = True
            parts = attrs.get("content", "").split(";", 1)
            if len(parts) == 2:
                key, separator, value = parts[1].strip().partition("=")
                if separator and key.strip().lower() == "url":
                    self.advance_url = value.strip().strip("\"'")
        if tag == "svg":
            self.svg_depth += 1
        if self.svg_depth and all(key in attrs for key in (
            "data-rdf-subject", "data-rdf-predicate", "data-rdf-object",
        )):
            self.edges.add(tuple(attrs[key] for key in (
                "data-rdf-subject", "data-rdf-predicate", "data-rdf-object",
            )))

    def handle_endtag(self, tag):
        if tag == "svg":
            self.svg_depth -= 1


def _files(directory):
    return {path.relative_to(directory): path.read_bytes()
            for path in directory.rglob("*") if path.is_file()}


def test_it_59_r3_s3_navigates_stage_results_and_pauses_or_resumes_playback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    ns = Namespace(f"urn:uad36:test:it59r3s3:{uuid4().hex}:")
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
    for run_index in range(1):
        token = uuid4().hex
        run = URIRef(f"https://dynamicontology.com/uad36/construction/run/{token}")
        directory = output_root / token
        directory.mkdir(parents=True)
        batch = Graph()
        results = {}
        for row_index in range(1):
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
    url = f"/constraint-workbench/runs/{token}"
    originals = _files(tmp_path)

    def read_page(response, stage_index, playback):
        assert response.status_code == 200
        page = _NavigationPage()
        page.feed(response.text)
        assert page.states == [playback], (
            "IT-59R3S3 requires visualization controls with an explicit playing/paused state."
        )
        result_id, path, _ = results[0, stage_index]
        assert page.selected == [str(result_id)]
        assert page.run_ids == [str(run)]
        assert page.refresh == (playback == "playing"), (
            "Playback must advance automatically while playing and remain still when paused."
        )
        expected = Graph().parse(path, format="turtle")
        assert page.edges == {tuple(str(term) for term in triple) for triple in expected}
        if playback == "playing" and stage_index < len(STAGES) - 1:
            assert page.advance_url, "Playing must advance to the next result, not just reload the same snapshot."
            target = urlsplit(page.advance_url)
            assert not target.scheme and not target.netloc and target.path == url
            query = parse_qs(target.query)
            assert query.get("result_id") == [str(results[0, stage_index + 1][0])]
            assert query.get("playback") == ["playing"]
        return page

    def action_url(page, action, stage_index, playback):
        links = page.controls.get(action, [])
        assert len(links) == 1, f"Provide exactly one active {action} control."
        parsed = urlsplit(links[0])
        assert not parsed.scheme and not parsed.netloc and parsed.path == url
        query = parse_qs(parsed.query)
        assert query.get("result_id") == [str(results[0, stage_index][0])]
        assert query.get("playback") == [playback]
        return links[0]

    with TestClient(app, follow_redirects=False) as client:
        # Begin on the middle result so both neighboring controls are applicable.
        playing = read_page(client.get(url, params={
            "result_id": str(results[0, 1][0]), "playback": "playing",
        }), 1, "playing")
        paused_url = action_url(playing, "pause", 1, "paused")
        paused = read_page(client.get(paused_url), 1, "paused")
        # Reloading a paused page must keep the same result and playback mode.
        paused = read_page(client.get(paused_url), 1, "paused")
        first = read_page(client.get(action_url(paused, "previous", 0, "paused")), 0, "paused")
        assert not first.controls.get("previous"), "Do not navigate before the first available result."
        middle = read_page(client.get(action_url(first, "next", 1, "paused")), 1, "paused")
        last = read_page(client.get(action_url(middle, "next", 2, "paused")), 2, "paused")
        assert not last.controls.get("next"), "Do not navigate beyond the last available result."
        # Select the first stage directly from the last stage, skipping the middle.
        direct_links = last.controls.get("select", [])
        direct_by_result = {}
        for href in direct_links:
            parsed = urlsplit(href)
            assert not parsed.scheme and not parsed.netloc and parsed.path == url
            query = parse_qs(parsed.query)
            assert query.get("playback") == ["paused"]
            assert len(query.get("result_id", [])) == 1
            key = query["result_id"][0]
            assert key not in direct_by_result
            direct_by_result[key] = href
        assert set(direct_by_result) == {str(item[0]) for item in results.values()}, (
            "Direct selection must offer every available stage result in this run."
        )
        first = read_page(client.get(direct_by_result[str(results[0, 0][0])]), 0, "paused")
        resumed = read_page(client.get(action_url(first, "resume", 0, "playing")), 0, "playing")
        read_page(client.get(resumed.advance_url), 1, "playing")
    assert _files(tmp_path) == originals, "Visualization navigation modified persisted run artifacts."
