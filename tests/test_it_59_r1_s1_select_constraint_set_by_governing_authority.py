"""IT-59R1S1: list registered constraint sets by explicit governing authority."""

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


class _WorkbenchPage(HTMLParser):
    """Read visible table cells and the authority selection without CSS coupling."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: dict[str, list[str]] = {}
        self.selected_authorities: list[str] = []
        self.has_authority_selector = False
        self._inside_authorities = False
        self._row_id: str | None = None
        self._cells: list[str] = []
        self._cell_parts: list[str] | None = None

    def handle_starttag(self, tag: str, attrs) -> None:
        attributes = dict(attrs)
        if tag == "select" and attributes.get("name") == "authority":
            self.has_authority_selector = True
            self._inside_authorities = True
        if tag == "option" and self._inside_authorities and "selected" in attributes:
            self.selected_authorities.append(attributes.get("value") or "")
        if tag == "tr" and attributes.get("data-constraint-set-id"):
            self._row_id = attributes["data-constraint-set-id"]
            self._cells = []
        if tag == "td" and self._row_id is not None:
            self._cell_parts = []

    def handle_data(self, data: str) -> None:
        if self._cell_parts is not None:
            self._cell_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "select":
            self._inside_authorities = False
        if tag == "td" and self._cell_parts is not None:
            self._cells.append(" ".join("".join(self._cell_parts).split()))
            self._cell_parts = None
        if tag == "tr" and self._row_id is not None:
            assert self._row_id not in self.rows, "A constraint set was listed more than once."
            self.rows[self._row_id] = self._cells
            self._row_id = None
            self._cells = []


@pytest.mark.parametrize("authority_index", [0, 1, 2], ids=["fannie-mae", "freddie-mac", "lender"])
def test_it_59_r1_s1_lists_constraint_sets_for_selected_governing_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    authority_index: int,
) -> None:
    ns = Namespace(f"urn:uad36:test:it59r1s1:{uuid4().hex}:")
    authorities = (
        (ns.fannie_mae, "Fannie Mae"),
        (ns.freddie_mac, "Freddie Mac"),
        (ns.lender, "Lender 12"),
    )
    # Two registered versions for one authority ensure the workbench does
    # not collapse releases, infer versions from labels, or list only the
    # active compliance workbook. Deliberately misleading filenames ensure
    # authority selection follows the RDF relationship, not a path search.
    registrations = (
        (ns.set_a, ns.fannie_mae, ns.workbook_a, "First governed release",
         "freddie-named-source.xlsm", "Governed Rules v1.5", "1.5"),
        (ns.set_b, ns.fannie_mae, ns.workbook_b, "Second governed release",
         "another-source.xlsx", "Governed Rules v1.6", "1.6"),
        (ns.set_c, ns.freddie_mac, ns.workbook_c, "Third governed release",
         "fannie-named-source.xlsx", "Freddie Rule Data", "2.0"),
        (ns.set_d, ns.lender, ns.workbook_d, "Lender supplemental requirements",
         "lender-rules.xlsx", "Lender & AMC Rules", "2026.10"),
    )
    registry = Graph()
    for triple in (
        (ns.configuration, RDF.type, CFG.ApplicationConfiguration),
        (ns.configuration, CFG.hasSourceWorkbooks, ns.workbooks),
        (ns.configuration, CFG.hasConstraintSets, ns.constraint_sets),
        (ns.configuration, CFG.activeComplianceSource, ns.workbook_c),
        (ns.workbooks, RDF.type, CFG.GovernedSourceWorkbookCollection),
        (ns.constraint_sets, RDF.type, CFG.GovernedConstraintSetCollection),
    ):
        registry.add(triple)
    for authority, label in authorities:
        registry.add((authority, RDF.type, CFG.GoverningAuthority))
        registry.add((authority, RDFS.label, Literal(label)))
    for set_id, authority, workbook_id, label, filename, worksheet, version in registrations:
        for triple in (
            (ns.constraint_sets, CFG.containsConstraintSet, set_id),
            (set_id, RDF.type, CFG.GovernedConstraintSet),
            (set_id, RDFS.label, Literal(label)),
            (set_id, CFG.governingAuthority, authority),
            (set_id, CFG.sourceWorkbook, workbook_id),
            (set_id, CFG.governedVersion, Literal(version)),
            (ns.workbooks, CFG.containsWorkbook, workbook_id),
            (workbook_id, RDF.type, CFG.GovernedSourceArtifact),
            (workbook_id, CFG.sourceFileLocation, Literal(str(tmp_path / filename))),
            (workbook_id, CFG.ruleDataSheetName, Literal(worksheet)),
            (workbook_id, CFG.sourceFormat, Literal(Path(filename).suffix.lstrip("."))),
        ):
            registry.add(triple)
    configuration_path = tmp_path / "configuration.ttl"
    registry.serialize(destination=configuration_path, format="turtle")
    before = configuration_path.read_bytes()
    monkeypatch.setattr(app.state, "configuration_file", configuration_path)

    def no_build(*args, **kwargs):
        pytest.fail("Selecting a governing authority must not start constraint construction.")

    pipeline = import_module("app.services.constraint_production_pipeline")
    for operation_name in (
        "process_governed_source_row", "process_all_governed_source_rows",
        "resume_governed_source_row",
    ):
        monkeypatch.setattr(pipeline, operation_name, no_build)
    selected_authority = authorities[authority_index][0]
    # Proposed UI boundary: a normal GET form selects the authority. Each
    # visible result row carries its exact governed set IRI in a data attribute.
    # Listing uses registration metadata; it does not parse workbook contents.
    with TestClient(app, follow_redirects=False) as client:
        response = client.get(
            "/constraint-workbench",
            params={"authority": str(selected_authority)},
        )
    assert response.status_code == 200, (
        "IT-59R1S1 requires a constraint-workbench page that lists registered "
        "constraint sets for the selected governing authority. "
        f"Expected HTTP 200; got {response.status_code}."
    )
    assert "text/html" in response.headers.get("content-type", "")
    page = _WorkbenchPage()
    page.feed(response.text)
    assert page.has_authority_selector, "The operator needs a governing-authority selector."
    assert page.selected_authorities == [str(selected_authority)]
    applicable = [registration for registration in registrations if registration[1] == selected_authority]
    assert set(page.rows) == {str(registration[0]) for registration in applicable}, (
        "The workbench must list every applicable registered set, preserve "
        "distinct versions, and exclude sets governed by another authority."
    )
    for set_id, _, _, label, filename, worksheet, version in applicable:
        cells = page.rows[str(set_id)]
        assert any(label in cell for cell in cells), "The registered set label is missing."
        assert any(filename in cell for cell in cells), "The source workbook is not identified."
        assert worksheet in cells, "The governed rule-data worksheet is not displayed."
        assert version in cells, "The explicit governed version is not displayed."
    assert configuration_path.read_bytes() == before, "Listing changed the governed registry."
    assert set(tmp_path.iterdir()) == {configuration_path}, "Selection unexpectedly created build artifacts."
