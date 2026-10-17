"""IT-60R2S1: preserve a leading-zero source identifier as text."""

from __future__ import annotations

from pathlib import Path

import pytest
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


@pytest.mark.parametrize(
    ("source_identifier", "number_format"),
    (
        pytest.param("0100.0007", "General", id="text-stored-identifier"),
        pytest.param(100.0007, "0000.0000", id="zero-padded-numeric-cell"),
    ),
)
def test_it_60_r2_s1_preserves_leading_zero_source_identifier_as_text(
    tmp_path: Path,
    source_identifier: str | float,
    number_format: str,
) -> None:
    workbook_path = tmp_path / "governed-compliance.xlsx"
    configuration_path = tmp_path / "configuration.ttl"

    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Governed rules"
    worksheet.append(CONSTRAINT_HEADERS)
    worksheet.append(
        (
            source_identifier,
            "SubjectAddress",
            "MESSAGE-1",
            "Governed message",
            "Governed rule condition",
            "Fatal",
            "Subject",
            "GSE",
            "Appendix H-1",
            "/REPORT/SUBJECT/ADDRESS/",
        )
    )
    worksheet["A2"].number_format = number_format
    workbook.save(workbook_path)
    workbook.close()

    graph = Graph()
    graph.bind("cfg", CFG)
    application = CFG.developer
    collection = CFG.sourceWorkbooks
    selected_workbook = CFG.activeWorkbook
    graph.add((application, RDF.type, CFG.ApplicationConfiguration))
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
            Literal("Governed rules"),
        )
    )
    graph.serialize(destination=configuration_path, format="turtle")

    result = gse_constraint_sources.read_active_compliance_workbook_rows(
        configuration_path=configuration_path,
    )

    identifier = result.rows[0]["Unique ID"]
    assert isinstance(identifier, str), (
        "A governed source identifier must be returned as text, never as a number."
    )
    assert identifier == "0100.0007", (
        "The reader must preserve the exact leading-zero identifier as governed "
        f"by the workbook; got {identifier!r}."
    )
