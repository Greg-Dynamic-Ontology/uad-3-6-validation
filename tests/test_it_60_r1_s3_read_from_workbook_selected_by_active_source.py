"""IT-60R1S3: read from the workbook selected by active configuration."""

from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook
from rdflib import Graph, Literal, Namespace, RDF

from app.services import gse_constraint_sources


CFG = Namespace("https://dynamicontology.com/uad36/configuration#")
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


def _write_workbook(path: Path, row_marker: str) -> None:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Configured rules"
    worksheet.append(CONSTRAINT_HEADERS)
    worksheet.append(
        (
            f"SOURCE-{row_marker}",
            f"DataElement-{row_marker}",
            f"MESSAGE-{row_marker}",
            f"Message from {row_marker}",
            f"Rule condition from {row_marker}",
            "Fatal",
            f"Property-{row_marker}",
            row_marker,
            f"Appendix-{row_marker}",
            f"/REPORT/{row_marker}/",
        )
    )
    workbook.save(path)
    workbook.close()


def _write_configuration(
    path: Path,
    fannie_workbook: Path,
    freddie_workbook: Path,
) -> None:
    graph = Graph()
    graph.bind("cfg", CFG)
    application = CFG.developer
    collection = CFG.sourceWorkbooks
    fannie_source = CFG.FannieMaeComplianceRulesWorkbook
    freddie_source = CFG.FreddieMacComplianceRulesWorkbook

    graph.add((application, RDF.type, CFG.ApplicationConfiguration))
    graph.add((application, CFG.hasSourceWorkbooks, collection))
    graph.add((collection, CFG.containsWorkbook, fannie_source))
    graph.add((collection, CFG.containsWorkbook, freddie_source))
    graph.add((application, CFG.activeComplianceSource, freddie_source))

    graph.add((fannie_source, CFG.sourceFileLocation, Literal(fannie_workbook.as_posix())))
    graph.add((fannie_source, CFG.ruleDataSheetName, Literal("Configured rules")))
    graph.add((freddie_source, CFG.sourceFileLocation, Literal(freddie_workbook.as_posix())))
    graph.add((freddie_source, CFG.ruleDataSheetName, Literal("Configured rules")))

    graph.serialize(destination=path, format="turtle")


def test_it_60_r1_s3_reads_only_workbook_selected_by_active_source_configuration(
    tmp_path: Path,
) -> None:
    fannie_workbook = tmp_path / "fannie-compliance.xlsx"
    freddie_workbook = tmp_path / "freddie-compliance.xlsx"
    configuration_path = tmp_path / "configuration.ttl"
    _write_workbook(fannie_workbook, "FANNIE")
    _write_workbook(freddie_workbook, "FREDDIE")
    _write_configuration(configuration_path, fannie_workbook, freddie_workbook)

    result = gse_constraint_sources.read_active_compliance_workbook_rows(
        configuration_path=configuration_path,
    )

    assert result.workbook_path == freddie_workbook.resolve(), (
        "The reader must use the workbook selected by cfg:activeComplianceSource."
    )
    assert result.worksheet_name == "Configured rules"
    assert [row["Message ID"] for row in result.rows] == ["MESSAGE-FREDDIE"]
    assert all(row["Source"] == "FREDDIE" for row in result.rows)
