"""IT-59R4S2: replay saved stage RDF with every construction entry point blocked.

Open the existing run page in playback mode, then follow its actual automatic
advance links to the last saved result. Each displayed graph must match the
original snapshot. The complete saved bundle and configuration must remain
byte-for-byte unchanged. No build workers, source-row processing, resume, or
set-build service may execute while reviewing a saved run.
"""
from hashlib import sha256
from importlib import import_module
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


def test_it_59_r4_s2_replays_saved_run_without_rerunning_construction(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    ns = Namespace(f"urn:uad36:test:it59r4s2:{uuid4().hex}:")
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
        # Model the saved replay index produced by IT-59R4S1.
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
    url = f"/constraint-workbench/runs/{token}"
    original_files = _files(tmp_path)
    attempted_construction = []

    def forbidden(name):
        def reject(*args, **kwargs):
            attempted_construction.append(name)
            pytest.fail(f"IT-59R4S2 replay must not execute construction: {name}")
        return reject

    operations = (
        ("constraint_production_pipeline", "process_all_governed_source_rows"),
        ("constraint_production_pipeline", "process_governed_source_row"),
        ("constraint_production_pipeline", "resume_governed_source_row"),
        ("constraint_set_build_workbench", "build_registered_constraint_set"),
        ("constraint_normalization_agent", "normalize_governed_constraint_to_file"),
        ("logical_schema_binding_agent", "bind_normalized_constraint_to_logical_schema"),
        ("context_resolution_agent", "resolve_bound_constraint_context"),
        ("constraint_behavior_classification", "classify_governed_constraint_behavior"),
        ("instance_rdf_binding_agent", "bind_governed_constraint_to_instance_rdf"),
        ("shacl_generation_agent", "generate_governed_constraint_shacl"),
    )
    routes = import_module("app.api.routes")
    pipeline = import_module("app.services.constraint_production_pipeline")
    for module_name, operation_name in operations:
        module = import_module(f"app.services.{module_name}")
        real_operation = getattr(module, operation_name)
        blocked = forbidden(f"{module_name}.{operation_name}")
        monkeypatch.setattr(module, operation_name, blocked)
        # Block imported aliases as well as calls through the defining module.
        for consumer in (routes, pipeline):
            if getattr(consumer, operation_name, None) is real_operation:
                monkeypatch.setattr(consumer, operation_name, blocked)

    href = url + "?playback=playing"
    seen = []
    with TestClient(app, follow_redirects=False) as client:
        for stage_index, stage in enumerate(STAGES):
            response = client.get(href)
            assert response.status_code == 200, (
                f"Saved-run replay could not open {stage}: HTTP {response.status_code}."
            )
            assert "text/html" in response.headers.get("content-type", "")
            page = _NavigationPage()
            page.feed(response.text)
            result_id, path, _ = results[0, stage_index]
            assert page.run_ids == [str(run)]
            assert page.selected == [str(result_id)], (
                "Replay must show the original saved result identities in pipeline order."
            )
            seen.append(page.selected[0])
            snapshot = Graph().parse(path, format="turtle")
            assert page.edges == {tuple(str(term) for term in triple) for triple in snapshot}, (
                "Replay must render the preserved stage graph instead of regenerating knowledge."
            )
            if stage_index + 1 < len(STAGES):
                assert page.refresh and page.advance_url, "Replay must advance to the next saved result."
                parsed = urlsplit(page.advance_url)
                assert not parsed.scheme and not parsed.netloc and parsed.path == url
                query = parse_qs(parsed.query)
                assert query.get("result_id") == [str(results[0, stage_index + 1][0])]
                assert query.get("playback") == ["playing"]
                href = page.advance_url
            else:
                assert not page.refresh, "Completed-run replay must stop at its last saved result."
                assert not page.controls.get("next")
            assert _files(tmp_path) == original_files, "Replaying a stage changed the saved bundle."
    assert seen == [str(results[0, index][0]) for index in range(len(STAGES))]
    assert not attempted_construction
    assert _files(tmp_path) == original_files
