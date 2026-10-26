"""IT-61R3S4: open provenance details for the displayed saved stage result.

Proposed native UI control: details#stage-provenance with a visible summary.
Its metadata identifies source workbook, worksheet, row, selected result and
that result's PROV.wasGeneratedBy activity. Visible details show the registered
workbook label/file, configured worksheet, exact row ID and stage activity IRI.

Two rows and multiple stages have distinct activities. A group-scoped run must
show the displayed result's own row, not the whole group's row IDs or a run-level
activity. Helpers and saved RDF fixtures are self-contained.
"""

from hashlib import sha256
from html.parser import HTMLParser
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook
from openpyxl.worksheet.worksheet import Worksheet
from rdflib import Graph, Literal, Namespace, RDF, RDFS, URIRef
from rdflib.namespace import PROV

from app.main import app
from app.services.construction_exchange import (
    UADEX, record_construction_stage_result, record_construction_stage_provenance,
)

CFG = Namespace("https://dynamicontology.com/uad36/configuration#")
CV = Namespace("https://dynamicontology.com/uad36/constraint-vocabulary#")
STAGES = ("normalized-constraint-representation", "logical-schema-binding")


class _ProvenancePage(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.run_ids = []
        self.selected = []
        self.details = []
        self._details = None
        self._depth = 0
        self._summary = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "data-build-run-id" in attrs:
            self.run_ids.append(attrs["data-build-run-id"])
        if "data-selected-stage-result-id" in attrs:
            self.selected.append(attrs["data-selected-stage-result-id"])
        if tag == "details":
            if self._details is not None:
                self._depth += 1
            elif attrs.get("id") == "stage-provenance":
                self._details = {"attributes": attrs, "summary": [], "text": []}
                self._depth = 1
        if tag == "summary" and self._details is not None:
            self._summary = True

    def handle_data(self, data):
        if self._details is not None:
            self._details["text"].append(data)
            if self._summary:
                self._details["summary"].append(data)

    def handle_endtag(self, tag):
        if tag == "summary":
            self._summary = False
        if tag == "details" and self._details is not None:
            self._depth -= 1
            if self._depth == 0:
                self.details.append(self._details)
                self._details = None


def _files(directory):
    return {path.relative_to(directory): path.read_bytes()
            for path in directory.rglob("*") if path.is_file()}


@pytest.mark.parametrize("row_scope, selected_row, selected_stage", [
    ("one", 0, 0), ("group", 1, 1),
], ids=["single-row-normalization", "group-selected-row-schema-binding"])
def test_it_61_r3_s4_shows_source_and_actual_stage_activity_in_provenance_details(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    row_scope: str, selected_row: int, selected_stage: int,
) -> None:
    ns = Namespace(f"urn:uad36:test:it61r3s4:{uuid4().hex}:")
    workbook_label = "Registered governed GSE workbook " + uuid4().hex
    worksheet = "PublishedGovernedRules"
    source_path = tmp_path / "registered-gse-source.xlsx"
    row_ids = tuple("0" + uuid4().hex for _ in range(2))
    workbook = Workbook()
    first_sheet = workbook.active
    assert isinstance(first_sheet, Worksheet)
    first_sheet.title = "NotTheRuleData"
    sheet = workbook.create_sheet(worksheet)
    sheet.append(["Unique ID"])
    for unique_id in row_ids:
        sheet.append([unique_id])
    workbook.save(source_path)
    workbook.close()
    token = uuid4().hex
    run = URIRef(f"https://dynamicontology.com/uad36/construction/run/{token}")
    output_root = tmp_path / "build-runs"
    directory = output_root / token
    directory.mkdir(parents=True)
    configuration = Graph()
    for triple in (
        (ns.configuration, RDF.type, CFG.ApplicationConfiguration),
        (ns.configuration, CFG.hasSourceWorkbooks, ns.workbooks),
        (ns.configuration, CFG.usesConstraintBuildProfile, ns.profile),
        (ns.profile, RDF.type, CFG.ConstraintBuildProfile),
        (ns.profile, CFG.buildOutputDirectory, Literal(str(output_root))),
        (ns.workbooks, RDF.type, CFG.GovernedSourceWorkbookCollection),
        (ns.workbooks, CFG.containsWorkbook, ns.workbook),
        (ns.workbook, RDF.type, CFG.GovernedSourceArtifact),
        (ns.workbook, RDFS.label, Literal(workbook_label)),
        (ns.workbook, CFG.sourceFileLocation, Literal(str(source_path))),
        (ns.workbook, CFG.ruleDataSheetName, Literal(worksheet)),
        (ns.workbook, CFG.sourceFormat, Literal("xlsx")),
    ):
        configuration.add(triple)
    configuration_path = tmp_path / "configuration.ttl"
    configuration.serialize(destination=configuration_path, format="turtle")
    monkeypatch.setattr(app.state, "configuration_file", configuration_path)
    batch = Graph()
    snapshots = {}
    included_rows = [0] if row_scope == "one" else [0, 1]
    for row_index in included_rows:
        constraint = ns[f"constraint-{row_index}"]
        source = URIRef(f"urn:uad36:governed-source:{source_path.name}#{worksheet}!A{row_index + 2}:Q{row_index + 2}")
        knowledge = Graph()
        knowledge.add((constraint, RDF.type, CV.NormalizedConstraint))
        knowledge.add((constraint, CV.governedUniqueId, Literal(row_ids[row_index])))
        knowledge.add((constraint, PROV.wasDerivedFrom, source))
        row_directory = directory / "constraints" / uuid4().hex
        row_directory.mkdir(parents=True)
        for stage_index, stage in enumerate(STAGES):
            record = record_construction_stage_result(
                output_graph=knowledge, constraint_id=str(constraint),
                construction_stage=stage, construction_status="GREEN",
            )
            knowledge.add((record.result_id, UADEX.availableForDownstream, Literal(True)))
            activity = ns[f"execution-{uuid4().hex}"]
            record_construction_stage_provenance(
                output_graph=knowledge, result_id=str(record.result_id),
                activity_id=str(activity), agent_id=str(ns.worker),
                used_knowledge_ids=[str(source)],
            )
            path = row_directory / f"{stage_index + 1:02d}-{stage}.ttl"
            knowledge.add((record.result_id, UADEX.rdfSnapshotPath, Literal(str(path))))
            knowledge.serialize(destination=path, format="turtle")
            for triple in knowledge:
                batch.add(triple)
            batch.set((record.result_id, UADEX.snapshotSha256, Literal(sha256(path.read_bytes()).hexdigest())))
            snapshots[row_index, stage_index] = (record.result_id, activity, source)
    batch_path = directory / "batch-results.ttl"
    batch.serialize(destination=batch_path, format="turtle")
    manifest = Graph()
    for triple in (
        (run, RDF.type, CV.ConstraintPipelineRun),
        (run, RDF.type, PROV.Activity),
        (run, CV.sourceWorkbook, ns.workbook),
        (run, CV.sourceWorksheet, Literal(worksheet)),
        (run, CV.sourceWorkbookArtifact, URIRef(source_path.as_uri())),
        (run, CV.rowScope, Literal(row_scope)),
        (run, CV.status, Literal("COMPLETE")),
        (run, CV.batchResultsArtifact, URIRef(batch_path.as_uri())),
    ):
        manifest.add(triple)
    for index in included_rows:
        manifest.add((run, CV.governedUniqueId, Literal(row_ids[index])))
    manifest.serialize(destination=directory / "run.ttl", format="turtle")
    originals = _files(tmp_path)
    result, activity, source = snapshots[selected_row, selected_stage]
    with TestClient(app, follow_redirects=False) as client:
        response = client.get(f"/constraint-workbench/runs/{token}", params={
            "result_id": str(result), "playback": "paused",
        })
    assert response.status_code == 200
    page = _ProvenancePage()
    page.feed(response.text)
    assert page.run_ids == [str(run)]
    assert page.selected == [str(result)]
    assert len(page.details) == 1, (
        "IT-61R3S4 requires an operator-openable provenance details control "
        "for the currently displayed stage RDF result."
    )
    details = page.details[0]
    assert "provenance" in " ".join(details["summary"]).casefold()
    attrs = details["attributes"]
    assert attrs.get("data-stage-result-id") == str(result)
    assert attrs.get("data-source-workbook-id") == str(ns.workbook)
    assert attrs.get("data-source-worksheet") == worksheet
    assert attrs.get("data-source-row-id") == row_ids[selected_row]
    assert attrs.get("data-stage-activity-id") == str(activity), (
        "Show the activity that generated this result, not the run or another worker's activity."
    )
    visible = " ".join(" ".join(details["text"]).split())
    for expected in (workbook_label, source_path.name, worksheet, row_ids[selected_row], str(activity)):
        assert expected in visible
    assert row_ids[1 - selected_row] not in visible
    assert str(run) not in visible, "A build-run activity must not replace the selected worker's execution identity."
    assert _files(tmp_path) == originals
