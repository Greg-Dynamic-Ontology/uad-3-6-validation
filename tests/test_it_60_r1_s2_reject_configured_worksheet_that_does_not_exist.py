"""IT-60R1S2: reject a configured worksheet that does not exist."""

from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook
from rdflib import Graph, Literal, Namespace, RDF

from app.services import gse_constraint_sources


CFG = Namespace("https://dynamicontology.com/uad36/configuration#")
APP_CONFIGURATION = CFG.ApplicationConfiguration
CONSTRAINT_HEADERS = (
    "Unique ID",
    "Primary Data Element",
    "Message ID",
    "Message Text",
    "Rule Logic",
    "Severity",
    "Property Affected",
    "Source",
    "Source Document",
    " xPath",
)


def _write_workbook_with_an_alternate_usable_sheet(path: Path) -> None:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Available worksheet"
    worksheet.append(CONSTRAINT_HEADERS)
    worksheet.append(
        (
            "0100.0007",
            "SubjectAddress",
            "UAD1001",
            "A governed message",
            "A governed rule condition",
            "Fatal",
            "Subject",
            "GSE",
            "Appendix H-1",
            "/REPORT/SUBJECT/ADDRESS/",
        )
    )
    workbook.save(path)
    workbook.close()


def _write_configuration(
    path: Path,
    workbook_path: Path,
) -> None:
    graph = Graph()
    graph.bind("cfg", CFG)
    application = CFG.developer
    collection = CFG.sourceWorkbooks
    selected_workbook = CFG.testWorkbook

    graph.add((application, RDF.type, APP_CONFIGURATION))
    graph.add((application, CFG.hasSourceWorkbooks, collection))
    graph.add((application, CFG.activeComplianceSource, selected_workbook))
    graph.add((collection, CFG.containsWorkbook, selected_workbook))
    graph.add(
        (
            selected_workbook,
            CFG.sourceFileLocation,
            Literal(workbook_path.as_posix()),
        )
    )
    graph.add(
        (
            selected_workbook,
            CFG.ruleDataSheetName,
            Literal("Missing configured worksheet"),
        )
    )
    graph.serialize(destination=path, format="turtle")


def test_it_60_r1_s2_rejects_configured_worksheet_that_does_not_exist(
    tmp_path: Path,
) -> None:
    workbook_path = tmp_path / "governed-compliance.xlsx"
    configuration_path = tmp_path / "configuration.ttl"
    _write_workbook_with_an_alternate_usable_sheet(workbook_path)
    _write_configuration(configuration_path, workbook_path)

    try:
        gse_constraint_sources.read_active_compliance_workbook_rows(
            configuration_path=configuration_path,
        )
    except Exception as error:
        assert type(error).__name__ == "GovernedWorkbookConfigurationError", (
            "A missing configured worksheet must raise the contracted "
            "GovernedWorkbookConfigurationError, not a generic exception; "
            f"got {type(error).__name__}: {error}"
        )
    else:
        raise AssertionError(
            "The reader must reject a missing configured worksheet instead of "
            "silently selecting the available worksheet."
        )
