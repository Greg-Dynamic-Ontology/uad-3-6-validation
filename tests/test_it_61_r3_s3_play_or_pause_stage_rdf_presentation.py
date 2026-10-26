"""IT-61R3S3: play, pause and resume saved stage RDF in execution order.

Follow the UI's real Resume/Pause links and automatic meta-refresh targets.
Every presentation frame must identify its stage and original result, show the
exact saved Turtle and render the same RDF graph. A paused frame must not have
an automatic advance; resuming must retain that frame before advancing.
Construction entry points are blocked and saved artifacts remain unchanged.
All fixtures/helpers are local to this file.
"""
from hashlib import sha256
from importlib import import_module
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from rdflib import BNode, Graph, Literal, Namespace, RDF, URIRef
from rdflib.collection import Collection
from rdflib.compare import isomorphic
from rdflib.namespace import PROV, XSD
from rdflib.util import from_n3

from app.main import app
from app.services.construction_exchange import UADEX, record_construction_stage_result

CFG = Namespace("https://dynamicontology.com/uad36/configuration#")
CV = Namespace("https://dynamicontology.com/uad36/constraint-vocabulary#")
STAGES = ("normalized-constraint-representation", "logical-schema-binding", "context-resolution")


class _RdfPage(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.run_ids = []
        self.selected = []
        self.links = []
        self.edge_terms = []
        self.node_terms = []
        self.rdf_blocks = []
        self._rdf_parts = None
        self._svg_depth = 0
        self.incomplete_rdf_edges = 0
        self.unescaped_source_markup = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "data-build-run-id" in attrs:
            self.run_ids.append(attrs["data-build-run-id"])
        if "data-selected-stage-result-id" in attrs:
            self.selected.append(attrs["data-selected-stage-result-id"])
        if tag == "a" and attrs.get("data-visualization-action") == "select":
            self.links.append(attrs.get("href", ""))
        if tag == "svg":
            self._svg_depth += 1
        if self._svg_depth and "data-rdf-subject" in attrs:
            keys = ("data-rdf-subject-n3", "data-rdf-predicate-n3", "data-rdf-object-n3")
            if not all(key in attrs for key in keys):
                self.incomplete_rdf_edges += 1
            else:
                self.edge_terms.append(tuple(attrs[key] for key in keys))
        if self._svg_depth and "data-rdf-term-n3" in attrs:
            self.node_terms.append(attrs["data-rdf-term-n3"])
        if tag == "pre" and attrs.get("id") == "stage-rdf":
            self._rdf_parts = []
        if tag == "governed-note":
            self.unescaped_source_markup = True

    def handle_data(self, data):
        if self._rdf_parts is not None:
            self._rdf_parts.append(data)

    def handle_endtag(self, tag):
        if tag == "svg":
            self._svg_depth -= 1
        if tag == "pre" and self._rdf_parts is not None:
            self.rdf_blocks.append(''.join(self._rdf_parts))
            self._rdf_parts = None


def _files(directory):
    return {path.relative_to(directory): path.read_bytes()
            for path in directory.rglob("*") if path.is_file()}


class _SteppingPage(_RdfPage):
    def __init__(self):
        super().__init__()
        self.controls = {}
        self.headings = []
        self._heading_parts = None

    def handle_starttag(self, tag, attrs):
        super().handle_starttag(tag, attrs)
        attributes = dict(attrs)
        action = attributes.get("data-visualization-action")
        if tag == "a" and action in ("previous", "next") and attributes.get("aria-disabled") != "true":
            self.controls.setdefault(action, []).append(attributes.get("href", ""))
        if tag == "h2":
            self._heading_parts = []

    def handle_data(self, data):
        super().handle_data(data)
        if self._heading_parts is not None:
            self._heading_parts.append(data)

    def handle_endtag(self, tag):
        super().handle_endtag(tag)
        if tag == "h2" and self._heading_parts is not None:
            self.headings.append(" ".join("".join(self._heading_parts).split()))
            self._heading_parts = None


class _PlaybackPage(_SteppingPage):
    def __init__(self):
        super().__init__()
        self.playback_states = []
        self.refresh_targets = []
        self.refresh_count = 0

    def handle_starttag(self, tag, attrs):
        super().handle_starttag(tag, attrs)
        attributes = dict(attrs)
        if "data-playback-state" in attributes:
            self.playback_states.append(attributes["data-playback-state"])
        action = attributes.get("data-visualization-action")
        if tag == "a" and action in ("pause", "resume") and attributes.get("aria-disabled") != "true":
            self.controls.setdefault(action, []).append(attributes.get("href", ""))
        if tag == "meta" and attributes.get("http-equiv", "").lower() == "refresh":
            self.refresh_count += 1
            parts = attributes.get("content", "").split(";", 1)
            if len(parts) == 2:
                key, separator, value = parts[1].strip().partition("=")
                if separator and key.lower() == "url":
                    self.refresh_targets.append(value.strip().strip("\"'"))


def test_it_61_r3_s3_plays_pauses_and_resumes_rdf_with_stage_identity_preserved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    ns = Namespace(f"urn:uad36:test:it61r3s3:{uuid4().hex}:")
    token = uuid4().hex
    run = URIRef(f"https://dynamicontology.com/uad36/construction/run/{token}")
    output_root = tmp_path / "build-runs"
    directory = output_root / token
    row_directory = directory / "constraints" / uuid4().hex
    row_directory.mkdir(parents=True)
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
    knowledge = Graph()
    knowledge.bind("test", ns)
    knowledge.bind("cv", CV)
    knowledge.add((ns.constraint, RDF.type, CV.NormalizedConstraint))
    knowledge.add((ns.constraint, CV.governedUniqueId, Literal("0" + uuid4().hex)))
    knowledge.add((ns.constraint, PROV.wasDerivedFrom, ns.source_row))
    knowledge.add((ns.constraint, CV.requirementText,
                   Literal('Governed text & <governed-note>quoted "value"</governed-note> — café')))
    # Equal lexical spellings with distinct RDF identities must not collapse.
    for value in (Literal("present", lang="en"), Literal("present", lang="fr")):
        knowledge.add((ns.constraint, ns.annotation, value))
    knowledge.add((ns.constraint, ns.threshold, Literal("7", datatype=XSD.integer)))
    knowledge.add((ns.constraint, ns.threshold, Literal("7", datatype=XSD.string)))
    knowledge.add((ns.constraint, ns.reference, ns.named_resource))
    knowledge.add((ns.constraint, ns.reference, Literal(str(ns.named_resource))))
    head = BNode()
    knowledge.add((ns.constraint, ns.ordered_schema_path, head))
    Collection(knowledge, head, [ns.property_resource, ns.address_resource])
    batch = Graph()
    snapshots = []
    for index, stage in enumerate(STAGES):
        if index:
            knowledge.add((ns.constraint, CV.logicalSchemaResource, ns.address_resource))
        if index == 2:
            knowledge.add((ns.constraint, CV.applicableContext, ns.resolved_context))
        record = record_construction_stage_result(
            output_graph=knowledge, constraint_id=str(ns.constraint),
            construction_stage=stage, construction_status="GREEN",
        )
        knowledge.add((record.result_id, UADEX.availableForDownstream, Literal(True)))
        path = row_directory / f"{index + 1:02d}-{stage}.ttl"
        knowledge.add((record.result_id, UADEX.rdfSnapshotPath, Literal(str(path))))
        turtle = f"# Original governed serialization {uuid4().hex}\n\n" + knowledge.serialize(format="turtle")
        path.write_bytes(turtle.encode("utf-8"))
        for triple in knowledge:
            batch.add(triple)
        batch.set((record.result_id, UADEX.snapshotSha256, Literal(sha256(path.read_bytes()).hexdigest())))
        snapshots.append((record.result_id, path, turtle))
    batch_path = directory / "batch-results.ttl"
    batch.serialize(destination=batch_path, format="turtle")
    manifest = Graph()
    for triple in (
        (run, RDF.type, CV.ConstraintPipelineRun),
        (run, RDF.type, PROV.Activity),
        (run, CV.sourceWorkbook, ns.workbook),
        (run, CV.sourceWorksheet, Literal("GovernedRules")),
        (run, CV.status, Literal("COMPLETE")),
        (run, CV.batchResultsArtifact, URIRef(batch_path.as_uri())),
    ):
        manifest.add(triple)
    manifest.serialize(destination=directory / "run.ttl", format="turtle")
    originals = _files(tmp_path)
    attempted = []
    routes = import_module("app.api.routes")
    pipeline = import_module("app.services.constraint_production_pipeline")
    workbench = import_module("app.services.constraint_pipeline_workbench")

    def forbid(name):
        def rejected(*args, **kwargs):
            attempted.append(name)
            pytest.fail(f"IT-61R3S3 playback must use saved results without rerunning {name}.")
        return rejected

    for module, name in (
        (pipeline, "process_governed_source_row"),
        (pipeline, "process_all_governed_source_rows"),
        (pipeline, "resume_governed_source_row"),
        (pipeline, "_construct_governed_source"),
        (workbench, "process_one_workbook_row"),
        (workbench, "process_selected_workbook_rows"),
        (workbench, "process_all_workbook_rows"),
    ):
        real = getattr(module, name)
        blocked = forbid(name)
        monkeypatch.setattr(module, name, blocked)
        for consumer in (routes, pipeline, workbench):
            if getattr(consumer, name, None) is real:
                monkeypatch.setattr(consumer, name, blocked)
    url = f"/constraint-workbench/runs/{token}"
    presented = []

    def assert_frame(response, index, state):
        assert response.status_code == 200
        page = _PlaybackPage()
        page.feed(response.text)
        result, path, turtle = snapshots[index]
        assert page.playback_states == [state]
        assert page.run_ids == [str(run)]
        assert page.selected == [str(result)]
        assert any(STAGES[index] in heading for heading in page.headings)
        assert page.rdf_blocks == [turtle]
        assert page.edge_terms and not page.incomplete_rdf_edges
        graph = Graph()
        for edge in page.edge_terms:
            graph.add(tuple(from_n3(term) for term in edge))
        assert isomorphic(graph, Graph().parse(path, format="turtle"))
        assert not page.unescaped_source_markup
        if state == "paused":
            assert page.refresh_count == 0, "Paused playback must remain on the selected stage."
        assert _files(tmp_path) == originals
        return page

    def check_url(href, index, state):
        parsed = urlsplit(href)
        assert not parsed.scheme and not parsed.netloc and parsed.path == url
        query = parse_qs(parsed.query)
        assert query.get("result_id") == [str(snapshots[index][0])]
        assert query.get("playback") == [state]
        return href

    def control(page, action, index, state):
        links = page.controls.get(action, [])
        assert len(links) == 1, f"Provide one active {action} playback control."
        return check_url(links[0], index, state)

    def advance(page, index):
        assert page.refresh_count == 1 and len(page.refresh_targets) == 1, (
            "Playing must present the next available stage automatically."
        )
        return check_url(page.refresh_targets[0], index, "playing")

    with TestClient(app, follow_redirects=False) as client:
        paused = assert_frame(client.get(url, params={
            "result_id": str(snapshots[0][0]), "playback": "paused",
        }), 0, "paused")
        playing = assert_frame(client.get(control(paused, "resume", 0, "playing")), 0, "playing")
        presented.append(snapshots[0][0])
        middle = assert_frame(client.get(advance(playing, 1)), 1, "playing")
        presented.append(snapshots[1][0])
        pause_url = control(middle, "pause", 1, "paused")
        paused = assert_frame(client.get(pause_url), 1, "paused")
        paused = assert_frame(client.get(pause_url), 1, "paused")
        middle = assert_frame(client.get(control(paused, "resume", 1, "playing")), 1, "playing")
        last = assert_frame(client.get(advance(middle, 2)), 2, "playing")
        presented.append(snapshots[2][0])
        assert last.refresh_count == 0, "A completed run must stop advancing after its last stage result."
        assert not last.controls.get("next")
        assert_frame(client.get(control(last, "pause", 2, "paused")), 2, "paused")
    assert presented == [result for result, _, _ in snapshots]
    assert not attempted
    assert _files(tmp_path) == originals
