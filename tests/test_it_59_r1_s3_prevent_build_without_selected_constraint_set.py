"""IT-59R1S3: reject a build request that has no selected constraint set."""

from __future__ import annotations

from html.parser import HTMLParser
from importlib import import_module
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from rdflib import Graph, Literal, Namespace, RDF, RDFS

from app.main import app


CFG = Namespace("https://dynamicontology.com/uad36/configuration#")


class _VisiblePage(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.has_selected_input = False
        self._hidden_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in ("style", "script"):
            self._hidden_depth += 1
        if tag == "section" and dict(attrs).get("id") == "selected-build-input":
            self.has_selected_input = True

    def handle_endtag(self, tag: str) -> None:
        if tag in ("style", "script"):
            self._hidden_depth = max(0, self._hidden_depth - 1)

    def handle_data(self, data: str) -> None:
        if not self._hidden_depth:
            self.parts.append(data)

    @property
    def text(self) -> str:
        return " ".join(" ".join(self.parts).split())


@pytest.mark.parametrize("selection", [None, "", " \t "], ids=[
    "omitted-selection", "empty-selection", "whitespace-selection",
])
def test_it_59_r1_s3_prevents_build_when_no_constraint_set_is_selected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    selection: str | None,
) -> None:
    ns = Namespace(f"urn:uad36:test:it59r1s3:{uuid4().hex}:")
    # A valid registered set and an active workbook exist. Neither is an
    # implicit selection: the operator still has to choose the build input.
    registry = Graph()
    for triple in (
        (ns.configuration, RDF.type, CFG.ApplicationConfiguration),
        (ns.configuration, CFG.hasSourceWorkbooks, ns.workbooks),
        (ns.configuration, CFG.hasConstraintSets, ns.constraint_sets),
        (ns.configuration, CFG.activeComplianceSource, ns.workbook),
        (ns.workbooks, RDF.type, CFG.GovernedSourceWorkbookCollection),
        (ns.workbooks, CFG.containsWorkbook, ns.workbook),
        (ns.constraint_sets, RDF.type, CFG.GovernedConstraintSetCollection),
        (ns.constraint_sets, CFG.containsConstraintSet, ns.constraint_set),
        (ns.authority, RDF.type, CFG.GoverningAuthority),
        (ns.authority, RDFS.label, Literal("Registered governing authority")),
        (ns.constraint_set, RDF.type, CFG.GovernedConstraintSet),
        (ns.constraint_set, RDFS.label, Literal("Registered governed release")),
        (ns.constraint_set, CFG.governingAuthority, ns.authority),
        (ns.constraint_set, CFG.sourceWorkbook, ns.workbook),
        (ns.constraint_set, CFG.governedVersion, Literal("1.5")),
        (ns.workbook, RDF.type, CFG.GovernedSourceArtifact),
        (ns.workbook, CFG.sourceFileLocation, Literal(str(tmp_path / "registered-source.xlsx"))),
        (ns.workbook, CFG.ruleDataSheetName, Literal("Governed Rules")),
        (ns.workbook, CFG.sourceFormat, Literal("xlsx")),
    ):
        registry.add(triple)
    configuration_path = tmp_path / "configuration.ttl"
    registry.serialize(destination=configuration_path, format="turtle")
    original = configuration_path.read_bytes()
    monkeypatch.setattr(app.state, "configuration_file", configuration_path)
    pipeline_calls = []

    def forbidden_build(*args, **kwargs):
        pipeline_calls.append((args, kwargs))
        pytest.fail("The workbench started construction without a selected constraint set.")

    pipeline = import_module("app.services.constraint_production_pipeline")
    for name in (
        "process_governed_source_row", "process_all_governed_source_rows",
        "resume_governed_source_row",
    ):
        monkeypatch.setattr(pipeline, name, forbidden_build)
    with TestClient(app, follow_redirects=False) as client:
        listing = client.get("/constraint-workbench", params={"authority": str(ns.authority)})
        assert listing.status_code == 200
        page = _VisiblePage()
        page.feed(listing.text)
        assert not page.has_selected_input, "The workbench selected a set without an operator choice."
        data = {"authority": str(ns.authority)}
        if selection is not None:
            data["constraint_set_id"] = selection
        # Proposed build-action boundary. Missing input must be handled here
        # even when a request bypasses any browser-side selection validation.
        response = client.post("/constraint-workbench/build", data=data)
    assert not pipeline_calls
    assert configuration_path.read_bytes() == original
    assert set(tmp_path.iterdir()) == {configuration_path}, (
        "A rejected build request created construction artifacts."
    )
    assert response.status_code == 400, (
        "IT-59R1S3 requires the build action to reject a missing constraint-set "
        "selection with an operator-facing message and no construction run. "
        f"Expected HTTP 400; got {response.status_code}."
    )
    assert "text/html" in response.headers.get("content-type", ""), (
        "The workbench must display the selection error to the operator."
    )
    error_page = _VisiblePage()
    error_page.feed(response.text)
    assert not error_page.has_selected_input
    assert any(message in error_page.text.casefold() for message in (
        "select a constraint set", "choose a constraint set",
        "a constraint set must be selected",
    )), "The page must explain that a constraint set must be selected."
