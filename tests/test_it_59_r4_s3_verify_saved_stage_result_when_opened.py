"""IT-59R4S3: verify the original saved digest when a stage result is opened.

Proposed inspection contract: data-integrity-status reports MATCH or MISMATCH;
data-recorded-digest and data-computed-digest expose the SHA-256 comparison.
The selected result and run remain identified in both cases. A mismatch must
be explained visibly and must not render the changed RDF as the stage graph.
Verification must not change the snapshot, batch, manifest or configuration.

Both cases use real saved Turtle files. The modified case changes valid RDF
while retaining the original recorded digests; no production verifier is mocked.
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


class _IntegrityPage(_InspectionPage):
    def __init__(self):
        super().__init__()
        self.integrity = []
        self.visible = []
        self.hidden_depth = 0

    def handle_starttag(self, tag, attrs):
        super().handle_starttag(tag, attrs)
        attributes = dict(attrs)
        if tag in ("script", "style"):
            self.hidden_depth += 1
        if "data-integrity-status" in attributes:
            self.integrity.append((
                attributes["data-integrity-status"],
                attributes.get("data-recorded-digest"),
                attributes.get("data-computed-digest"),
            ))

    def handle_endtag(self, tag):
        super().handle_endtag(tag)
        if tag in ("script", "style"):
            self.hidden_depth -= 1

    def handle_data(self, data):
        super().handle_data(data)
        if not self.hidden_depth:
            self.visible.append(data)


@pytest.mark.parametrize("modified", [False, True], ids=["matching-snapshot", "modified-snapshot"])
def test_it_59_r4_s3_reports_saved_stage_integrity_when_opened(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, modified: bool,
) -> None:
    ns = Namespace(f"urn:uad36:test:it59r4s3:{uuid4().hex}:")
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
        for (row_index, ordinal), (result, snapshot_path, _) in results.items():
            manifest.add((run, CV.preservedStageResult, result))
            manifest.add((result, CV.stageOrder, Literal(ordinal + 1)))
            for predicate in (
                RDF.type, UADEX.forConstraint, UADEX.constructionStage,
                UADEX.constructionStatus, UADEX.rdfSnapshotPath, UADEX.snapshotSha256,
            ):
                for value in batch.objects(result, predicate):
                    manifest.add((result, predicate, value))
        manifest.serialize(destination=directory / "run.ttl", format="turtle")
        runs.append((token, run, results))

    token, run, results = runs[0]
    result, snapshot_path, original_turtle = results[0, 0]
    recorded_digest = sha256(snapshot_path.read_bytes()).hexdigest()
    assert recorded_digest == sha256(original_turtle.encode("utf-8")).hexdigest()
    if modified:
        changed = Graph().parse(snapshot_path, format="turtle")
        changed.add((ns["constraint-0"], CV.requirementText, Literal("Changed after saving " + uuid4().hex)))
        snapshot_path.write_bytes(changed.serialize(format="turtle").encode("utf-8"))
    computed_digest = sha256(snapshot_path.read_bytes()).hexdigest()
    assert (computed_digest != recorded_digest) == modified
    directory = output_root / token
    manifest_path = directory / "run.ttl"
    batch_path = directory / "batch-results.ttl"
    # The expected digest remains the original published value in both records.
    for path in (manifest_path, batch_path):
        saved = Graph().parse(path, format="turtle")
        assert set(saved.objects(result, UADEX.snapshotSha256)) == {Literal(recorded_digest)}
    originals = _files(tmp_path)
    with TestClient(app, follow_redirects=False) as client:
        response = client.get(f"/constraint-workbench/runs/{token}", params={
            "result_id": str(result), "playback": "paused",
        })
    expected_status_codes = (200, 409) if modified else (200,)
    assert response.status_code in expected_status_codes, (
        "IT-59R4S3 requires a stage-specific integrity report when opening saved RDF, "
        f"including digest mismatches; got HTTP {response.status_code}."
    )
    assert "text/html" in response.headers.get("content-type", "")
    page = _IntegrityPage()
    page.feed(response.text)
    expected_status = "MISMATCH" if modified else "MATCH"
    assert page.integrity == [(expected_status, recorded_digest, computed_digest)], (
        "IT-59R4S3 requires an explicit comparison between the original saved digest "
        "and the current snapshot bytes, reporting whether the selected result matches."
    )
    assert page.run_ids == [str(run)]
    assert page.selected_results == [str(result)]
    visible = " ".join(" ".join(page.visible).split()).casefold()
    if modified:
        assert any(phrase in visible for phrase in ("does not match", "mismatch", "integrity check failed"))
        assert not page.edges, "Changed RDF must not be rendered as a verified saved stage graph."
    else:
        assert any(phrase in visible for phrase in ("matches", "integrity verified", "integrity check passed"))
        graph = Graph().parse(snapshot_path, format="turtle")
        assert page.edges == {tuple(str(term) for term in triple) for triple in graph}
        assert page.rdf_blocks == [original_turtle]
    assert _files(tmp_path) == originals, (
        "Integrity verification must not repair, regenerate, or rewrite any saved artifact or digest."
    )
