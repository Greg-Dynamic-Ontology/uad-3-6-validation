"""IT-59R1S2: select exactly one registered constraint set as build input."""

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


class _SelectionPage(HTMLParser):
    """Read single-choice controls and the visible selected-input summary."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.radio_values: list[str] = []
        self.checked_values: list[str] = []
        self.selection_forms: list[dict] = []
        self.summaries: list[tuple[str, str]] = []
        self._form: dict | None = None
        self._summary_id: str | None = None
        self._summary_parts: list[str] = []
        self._summary_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        attributes = dict(attrs)
        if tag == "form":
            self._form = attributes
        if tag == "input" and attributes.get("type", "").lower() == "radio" and attributes.get("name") == "constraint_set_id":
            value = attributes.get("value") or ""
            self.radio_values.append(value)
            if "checked" in attributes:
                self.checked_values.append(value)
            if self._form is not None and self._form not in self.selection_forms:
                self.selection_forms.append(self._form)
        if tag == "section":
            if self._summary_id is not None:
                self._summary_depth += 1
            elif attributes.get("id") == "selected-build-input":
                self._summary_id = attributes.get("data-constraint-set-id") or ""
                self._summary_depth = 1
                self._summary_parts = []

    def handle_data(self, data: str) -> None:
        if self._summary_id is not None:
            self._summary_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "form":
            self._form = None
        if tag == "section" and self._summary_id is not None:
            self._summary_depth -= 1
            if self._summary_depth == 0:
                self.summaries.append((self._summary_id, " ".join(" ".join(self._summary_parts).split())))
                self._summary_id = None
                self._summary_parts = []


@pytest.mark.parametrize("selected_index", [0, 1], ids=["first-version", "second-version"])
def test_it_59_r1_s2_selects_one_registered_set_as_the_build_input(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    selected_index: int,
) -> None:
    ns = Namespace(f"urn:uad36:test:it59r1s2:{uuid4().hex}:")
    # Two versions under one authority and a third set under another ensure
    # the build input is the chosen set, not every listed or active source.
    registrations = (
        (ns.first_set, ns.authority, ns.first_workbook, "First governed release",
         "first-source.xlsm", "Rules v1.5", "1.5"),
        (ns.second_set, ns.authority, ns.second_workbook, "Second governed release",
         "second-source.xlsx", "Rules v1.6", "1.6"),
        (ns.other_set, ns.other_authority, ns.other_workbook, "Other authority release",
         "other-source.xlsx", "Other Rules", "2.0"),
    )
    registry = Graph()
    for triple in (
        (ns.configuration, RDF.type, CFG.ApplicationConfiguration),
        (ns.configuration, CFG.hasSourceWorkbooks, ns.workbooks),
        (ns.configuration, CFG.hasConstraintSets, ns.constraint_sets),
        (ns.configuration, CFG.activeComplianceSource, ns.other_workbook),
        (ns.workbooks, RDF.type, CFG.GovernedSourceWorkbookCollection),
        (ns.constraint_sets, RDF.type, CFG.GovernedConstraintSetCollection),
        (ns.authority, RDF.type, CFG.GoverningAuthority),
        (ns.authority, RDFS.label, Literal("Selected governing authority")),
        (ns.other_authority, RDF.type, CFG.GoverningAuthority),
        (ns.other_authority, RDFS.label, Literal("Other governing authority")),
    ):
        registry.add(triple)
    for set_id, authority, workbook, label, filename, worksheet, version in registrations:
        for triple in (
            (ns.constraint_sets, CFG.containsConstraintSet, set_id),
            (set_id, RDF.type, CFG.GovernedConstraintSet),
            (set_id, RDFS.label, Literal(label)),
            (set_id, CFG.governingAuthority, authority),
            (set_id, CFG.sourceWorkbook, workbook),
            (set_id, CFG.governedVersion, Literal(version)),
            (ns.workbooks, CFG.containsWorkbook, workbook),
            (workbook, RDF.type, CFG.GovernedSourceArtifact),
            (workbook, CFG.sourceFileLocation, Literal(str(tmp_path / filename))),
            (workbook, CFG.ruleDataSheetName, Literal(worksheet)),
            (workbook, CFG.sourceFormat, Literal(Path(filename).suffix.lstrip("."))),
        ):
            registry.add(triple)
    configuration_path = tmp_path / "configuration.ttl"
    registry.serialize(destination=configuration_path, format="turtle")
    original = configuration_path.read_bytes()
    monkeypatch.setattr(app.state, "configuration_file", configuration_path)

    def no_build(*args, **kwargs):
        pytest.fail("Choosing the build input must not itself start or resume construction.")

    pipeline = import_module("app.services.constraint_production_pipeline")
    for name in ("process_governed_source_row", "process_all_governed_source_rows", "resume_governed_source_row"):
        monkeypatch.setattr(pipeline, name, no_build)
    chosen = registrations[selected_index]
    previous = registrations[1 - selected_index]

    with TestClient(app, follow_redirects=False) as client:
        listing = client.get("/constraint-workbench", params={"authority": str(ns.authority)})
        assert listing.status_code == 200
        page = _SelectionPage()
        page.feed(listing.text)
        assert len(page.radio_values) == 2 and set(page.radio_values) == {
            str(registrations[0][0]), str(registrations[1][0]),
        }, (
            "IT-59R1S2 requires a single-choice constraint-set control for each "
            "applicable registered set, so the operator can select exactly one build input."
        )
        assert not page.checked_values, "A set was selected before the operator chose it."
        assert not page.summaries, "A build input was declared before selection."
        assert len(page.selection_forms) == 1
        form = page.selection_forms[0]
        assert form.get("method", "get").lower() == "get"
        assert form.get("action") == "/constraint-workbench"

        # First choose a different set, then change the selection. There must
        # be one current input, never an accumulation of earlier selections.
        for registration in (previous, chosen):
            response = client.get(
                form["action"],
                params={
                    "authority": str(ns.authority),
                    "constraint_set_id": str(registration[0]),
                },
            )
            assert response.status_code == 200
            assert "text/html" in response.headers.get("content-type", "")
            selected_page = _SelectionPage()
            selected_page.feed(response.text)
            assert selected_page.checked_values == [str(registration[0])], (
                "Exactly the operator-selected set must be checked."
            )
            assert len(selected_page.summaries) == 1, "The page must identify one current build input."
            selected_id, summary = selected_page.summaries[0]
            assert selected_id == str(registration[0])
            assert "Selected build input" in summary
            for text in (registration[3], registration[4], registration[5], registration[6]):
                assert text in summary, "The selected input must identify its label, workbook, worksheet, and version."
            for other in registrations:
                if other[0] != registration[0]:
                    assert other[3] not in summary, "An unselected set was included in the build input."
    assert configuration_path.read_bytes() == original
    assert set(tmp_path.iterdir()) == {configuration_path}, "Selection created construction artifacts."
