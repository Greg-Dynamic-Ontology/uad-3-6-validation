"""IT-59R5S1: show contracted failure knowledge for the selected build run.

Proposed HTML contract: the run exposes data-run-status; each failed worker
result has a data-construction-exception-id section with data-failed-stage,
data-source-constraint-id and, when recorded, data-source-row-id. Its visible
content includes the contracted reason and review requirement. The pipeline
stage carries data-status="EXCEPTION" and the page heading identifies failure
or exceptions instead of successful completion.

Fixtures use the real governed exchange exception operation. Displaying them
must not change the saved batch, manifest or verified upstream RDF.
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
from app.services.construction_exchange import (
    UADEX, exchange_construction_stage_exception, record_construction_stage_result,
)

CFG = Namespace("https://dynamicontology.com/uad36/configuration#")
CV = Namespace("https://dynamicontology.com/uad36/constraint-vocabulary#")


class _FailurePage(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.run_ids = []
        self.statuses = []
        self.stages = {}
        self.exceptions = []
        self.headings = []
        self._heading = None
        self._exception = None
        self._section_depth = 0
        self.unescaped_markup = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "data-build-run-id" in attrs:
            self.run_ids.append(attrs["data-build-run-id"])
        if "data-run-status" in attrs:
            self.statuses.append(attrs["data-run-status"])
        if "data-pipeline-stage" in attrs:
            self.stages[attrs["data-pipeline-stage"]] = attrs.get("data-status")
        if tag == "h1":
            self._heading = []
        if tag == "section":
            if self._exception is not None:
                self._section_depth += 1
            elif "data-construction-exception-id" in attrs:
                self._exception = {"attributes": attrs, "text": []}
                self._section_depth = 1
        if tag == "governed-detail":
            self.unescaped_markup = True

    def handle_data(self, data):
        if self._heading is not None:
            self._heading.append(data)
        if self._exception is not None:
            self._exception["text"].append(data)

    def handle_endtag(self, tag):
        if tag == "h1" and self._heading is not None:
            self.headings.append(" ".join("".join(self._heading).split()))
            self._heading = None
        if tag == "section" and self._exception is not None:
            self._section_depth -= 1
            if not self._section_depth:
                self.exceptions.append(self._exception)
                self._exception = None


def _saved_files(directory):
    return {path.relative_to(directory): path.read_bytes()
            for path in directory.rglob("*") if path.is_file()}


@pytest.mark.parametrize("failed_stage, iteration, row_available, run_status", [
    ("context-resolution", "IT-53", True, "COMPLETE_WITH_EXCEPTIONS"),
    ("shacl-representation", "IT-56", True, "COMPLETE_WITH_EXCEPTIONS"),
    ("logical-schema-binding", "IT-52", False, "EXCEPTION"),
], ids=["context-exception", "shacl-exception", "row-identifier-unavailable"])
def test_it_59_r5_s1_shows_failure_stage_source_and_contracted_reason(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    failed_stage: str, iteration: str, row_available: bool, run_status: str,
) -> None:
    ns = Namespace(f"urn:uad36:test:it59r5s1:{uuid4().hex}:")
    token = uuid4().hex
    run = URIRef(f"https://dynamicontology.com/uad36/construction/run/{token}")
    row_id = "0" + uuid4().hex
    reason = f"Cannot determine governed knowledge: {uuid4().hex} & <governed-detail>review required</governed-detail>."
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
    batch = Graph()
    batch.add((ns.constraint, RDF.type, CV.NormalizedConstraint))
    batch.add((ns.constraint, PROV.wasDerivedFrom, ns.source_row))
    if row_available:
        batch.add((ns.constraint, CV.governedUniqueId, Literal(row_id)))
    upstream = record_construction_stage_result(
        output_graph=batch, constraint_id=str(ns.constraint),
        construction_stage="normalized-constraint-representation", construction_status="GREEN",
    )
    snapshot_path = row_directory / "01-normalized-constraint.ttl"
    batch.add((upstream.result_id, UADEX.rdfSnapshotPath, Literal(str(snapshot_path))))
    batch.serialize(destination=snapshot_path, format="turtle")
    batch.add((upstream.result_id, UADEX.snapshotSha256,
               Literal(sha256(snapshot_path.read_bytes()).hexdigest())))
    exception = exchange_construction_stage_exception(
        exchange_graph=batch, constraint_id=str(ns.constraint), construction_stage=failed_stage,
        exception_reason=reason, requires_review=True,
    )
    batch.add((exception.result_id, PROV.wasDerivedFrom, ns.source_row))
    if row_available:
        batch.add((exception.result_id, CV.governedUniqueId, Literal(row_id)))
    batch_path = directory / "batch-results.ttl"
    batch.serialize(destination=batch_path, format="turtle")
    manifest = Graph()
    for triple in (
        (run, RDF.type, CV.ConstraintSetBuildRun),
        (run, RDF.type, PROV.Activity),
        (run, CV.selectedConstraintSet, ns.constraint_set),
        (run, CV.sourceVersion, Literal("test-release")),
        (run, CV.sourceWorkbook, ns.workbook),
        (run, CV.status, Literal(run_status)),
        (run, CV.productionException, exception.result_id),
        (run, CV.batchResultsArtifact, URIRef(batch_path.as_uri())),
    ):
        manifest.add(triple)
    manifest.serialize(destination=directory / "run.ttl", format="turtle")
    originals = _saved_files(tmp_path)
    with TestClient(app, follow_redirects=False) as client:
        response = client.get(f"/constraint-workbench/runs/{token}")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    page = _FailurePage()
    page.feed(response.text)
    assert page.run_ids == [str(run)]
    assert page.statuses == [run_status], (
        "IT-59R5S1 requires the visualization to expose this run's actual exception state."
    )
    assert page.stages.get(iteration) == "EXCEPTION", "Identify the worker stage that failed."
    assert len(page.exceptions) == 1, "Display the contracted production exception."
    failure = page.exceptions[0]
    attrs = failure["attributes"]
    assert attrs.get("data-construction-exception-id") == str(exception.result_id)
    assert attrs.get("data-failed-stage") == failed_stage
    assert attrs.get("data-source-constraint-id") == str(ns.source_row)
    text = " ".join(" ".join(failure["text"]).split())
    assert reason in text, "Preserve the exact contracted exception reason in visible text."
    assert str(ns.source_row) in text, "Show governed source traceability for the failure."
    assert "review" in text.casefold()
    if row_available:
        assert attrs.get("data-source-row-id") == row_id
        assert row_id in text
    else:
        assert not attrs.get("data-source-row-id"), "Do not invent an unavailable source-row ID."
        assert "unavailable" in text.casefold() or "not recorded" in text.casefold()
    assert any(any(word in heading.casefold() for word in ("exception", "failed", "failure"))
               for heading in page.headings), "The heading must identify an unsuccessful build state."
    assert not page.unescaped_markup, "Display contracted knowledge as text, not executable HTML."
    assert _saved_files(tmp_path) == originals
