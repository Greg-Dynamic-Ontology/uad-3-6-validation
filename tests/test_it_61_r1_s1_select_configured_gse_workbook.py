"""IT-61R1S1: select a registered workbook as run-specific UI input.

Proposed UI contract:
* GET /constraint-pipeline offers source_workbook_id choices from the configured
  hasSourceWorkbooks/containsWorkbook collection, using exact workbook IRIs.
* A GET selection identifies the workbook and configured rule-data worksheet in
  section#selected-source-workbook with data-source-workbook-id.
* The construction form POSTs to /constraint-pipeline/runs and carries exactly
  the selected source_workbook_id. Future row-scope scenarios start the run.

Choosing a source must not rewrite activeComplianceSource, modify any workbook,
create artifacts, or execute construction. No constraint-set registry is needed
for this workbook selection scenario. Helpers and fixtures are self-contained.
"""

from html.parser import HTMLParser
from importlib import import_module
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook
from openpyxl.worksheet.worksheet import Worksheet
from rdflib import Graph, Literal, Namespace, RDF, RDFS

from app.main import app

CFG = Namespace("https://dynamicontology.com/uad36/configuration#")


class _SourcePage(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.choices = {}
        self.checked = []
        self.summaries = []
        self.forms = []
        self._source_select = False
        self._option = None
        self._form = None
        self._summary = None
        self._summary_depth = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "form":
            self._form = {"attributes": attrs, "inputs": []}
            self.forms.append(self._form)
        if tag == "input" and self._form is not None:
            self._form["inputs"].append(attrs)
        if tag == "select" and attrs.get("name") == "source_workbook_id":
            self._source_select = True
        if tag == "option" and self._source_select:
            self._option = {"value": attrs.get("value", ""), "text": []}
            if "selected" in attrs and attrs.get("value"):
                self.checked.append(attrs["value"])
        if tag == "section":
            if self._summary is not None:
                self._summary_depth += 1
            elif attrs.get("id") == "selected-source-workbook":
                self._summary = {"attributes": attrs, "text": []}
                self._summary_depth = 1

    def handle_data(self, data):
        if self._option is not None:
            self._option["text"].append(data)
        if self._summary is not None:
            self._summary["text"].append(data)

    def handle_endtag(self, tag):
        if tag == "option" and self._option is not None:
            if self._option["value"]:
                self.choices[self._option["value"]] = " ".join("".join(self._option["text"]).split())
            self._option = None
        if tag == "select":
            self._source_select = False
        if tag == "form":
            self._form = None
        if tag == "section" and self._summary is not None:
            self._summary_depth -= 1
            if self._summary_depth == 0:
                self.summaries.append(self._summary)
                self._summary = None


def _files(directory):
    return {path.relative_to(directory): path.read_bytes()
            for path in directory.rglob("*") if path.is_file()}


@pytest.mark.parametrize("selected_index", [0, 1], ids=["fannie-mae", "freddie-mac"])
def test_it_61_r1_s1_selects_configured_workbook_and_worksheet_for_the_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, selected_index: int,
) -> None:
    ns = Namespace(f"urn:uad36:test:it61r1s1:{uuid4().hex}:")
    registrations = []
    # Misleading filenames prevent the UI from guessing authority or worksheet.
    for index, (label, filename, worksheet) in enumerate((
        ("Fannie Mae governed compliance workbook", "freddie-named-file.xlsx", "Fannie Governed Rules"),
        ("Freddie Mac governed compliance workbook", "fannie-named-file.xlsx", "Freddie Governed Rules"),
    )):
        path = tmp_path / filename
        workbook = Workbook()
        default_sheet = workbook.active
        assert isinstance(default_sheet, Worksheet)
        default_sheet.title = "NotTheRuleData"
        default_sheet.append(["The configured rule-data worksheet must be used."])
        sheet = workbook.create_sheet(worksheet)
        sheet.append(["Unique ID", "Message ID"])
        sheet.append(["0" + uuid4().hex, "rule-" + uuid4().hex])
        workbook.save(path)
        workbook.close()
        registrations.append({
            "id": ns[f"workbook-{index}"], "label": label,
            "path": path, "worksheet": worksheet,
        })
    selected = registrations[selected_index]
    other = registrations[1 - selected_index]
    configuration = Graph()
    for triple in (
        (ns.configuration, RDF.type, CFG.ApplicationConfiguration),
        (ns.configuration, CFG.hasSourceWorkbooks, ns.workbooks),
        (ns.configuration, CFG.activeComplianceSource, other["id"]),
        (ns.workbooks, RDF.type, CFG.GovernedSourceWorkbookCollection),
        # A workbook-shaped resource outside the collection is not selectable.
        (ns.unregistered, RDF.type, CFG.GovernedSourceArtifact),
        (ns.unregistered, RDFS.label, Literal("Unregistered workbook")),
        (ns.unregistered, CFG.sourceFileLocation, Literal("unregistered.xlsx")),
        (ns.unregistered, CFG.ruleDataSheetName, Literal("Unregistered rules")),
    ):
        configuration.add(triple)
    for registration in registrations:
        for triple in (
            (ns.workbooks, CFG.containsWorkbook, registration["id"]),
            (registration["id"], RDF.type, CFG.GovernedSourceArtifact),
            (registration["id"], RDFS.label, Literal(registration["label"])),
            (registration["id"], CFG.sourceFileLocation, Literal(str(registration["path"]))),
            (registration["id"], CFG.ruleDataSheetName, Literal(registration["worksheet"])),
            (registration["id"], CFG.sourceFormat, Literal("xlsx")),
        ):
            configuration.add(triple)
    configuration_path = tmp_path / "configuration.ttl"
    configuration.serialize(destination=configuration_path, format="turtle")
    monkeypatch.setattr(app.state, "configuration_file", configuration_path)
    originals = _files(tmp_path)
    calls = []

    def no_construction(*args, **kwargs):
        calls.append(True)
        pytest.fail("Selecting a source must not start construction or persist a build run.")

    pipeline = import_module("app.services.constraint_production_pipeline")
    for name in ("process_governed_source_row", "process_all_governed_source_rows", "resume_governed_source_row"):
        real = getattr(pipeline, name)
        monkeypatch.setattr(pipeline, name, no_construction)
        routes = import_module("app.api.routes")
        if getattr(routes, name, None) is real:
            monkeypatch.setattr(routes, name, no_construction)
    service = import_module("app.services.constraint_set_build_workbench")
    real = service.build_registered_constraint_set
    monkeypatch.setattr(service, "build_registered_constraint_set", no_construction)
    routes = import_module("app.api.routes")
    if getattr(routes, "build_registered_constraint_set", None) is real:
        monkeypatch.setattr(routes, "build_registered_constraint_set", no_construction)

    with TestClient(app, follow_redirects=False) as client:
        response = client.get("/constraint-pipeline")
        assert response.status_code == 200, (
            "IT-61R1S1 requires a pipeline UI that offers the configured source-workbook "
            f"collection; got HTTP {response.status_code}."
        )
        page = _SourcePage()
        page.feed(response.text)
        assert page.choices == {str(item["id"]): item["label"] for item in registrations}
        selection_forms = [form for form in page.forms
                           if form["attributes"].get("method", "get").lower() == "get"
                           and form["attributes"].get("action") == "/constraint-pipeline"]
        assert selection_forms, "Provide a workbook-selection form."
        response = client.get("/constraint-pipeline", params={"source_workbook_id": str(selected["id"])})
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
        page = _SourcePage()
        page.feed(response.text)
        assert page.checked == [str(selected["id"])]
        assert len(page.summaries) == 1
        summary = page.summaries[0]
        assert summary["attributes"].get("data-source-workbook-id") == str(selected["id"])
        text = " ".join(" ".join(summary["text"]).split())
        for expected in (selected["label"], selected["path"].name, selected["worksheet"]):
            assert expected in text
        assert other["label"] not in text and other["worksheet"] not in text
        run_forms = [form for form in page.forms
                     if form["attributes"].get("method", "get").lower() == "post"
                     and form["attributes"].get("action") == "/constraint-pipeline/runs"]
        assert len(run_forms) == 1, "The selected workbook must be carried into one construction-run form."
        values = [item.get("value", "") for item in run_forms[0]["inputs"]
                  if item.get("name") == "source_workbook_id"]
        assert values == [str(selected["id"])], "The run form must contain only the selected workbook identity."
        # A different selection must replace the run input without changing the registry.
        response = client.get("/constraint-pipeline", params={"source_workbook_id": str(other["id"])})
        assert response.status_code == 200
        changed = _SourcePage()
        changed.feed(response.text)
        assert changed.checked == [str(other["id"])]
        forms = [form for form in changed.forms if form["attributes"].get("action") == "/constraint-pipeline/runs"]
        assert len(forms) == 1
        assert [item.get("value", "") for item in forms[0]["inputs"]
                if item.get("name") == "source_workbook_id"] == [str(other["id"])]
    saved_configuration = Graph().parse(configuration_path, format="turtle")
    assert set(saved_configuration.objects(ns.configuration, CFG.activeComplianceSource)) == {other["id"]}
    assert _files(tmp_path) == originals, "Source selection modified a workbook, configuration or run artifacts."
    assert not calls
