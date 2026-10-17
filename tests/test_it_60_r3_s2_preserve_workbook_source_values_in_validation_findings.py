"""IT-60R3S2: retain active-workbook source values in findings."""

from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree as ET

from openpyxl import Workbook
from rdflib import Graph, Literal, Namespace, RDF

from app.models.enums import Investor
from app.services import required_data


CFG = Namespace("https://dynamicontology.com/uad36/configuration#")
MISMO = "http://www.mismo.org/residential/2009/schemas"
WORKSHEET_NAME = "Governed rules"
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


def _write_workbook(path: Path) -> None:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = WORKSHEET_NAME
    worksheet.append(CONSTRAINT_HEADERS)
    worksheet.append(
        (
            "0100.0007",
            "SubjectAddress",
            "TEST-IT60-R3S2",
            "Subject address is required by the governed workbook",
            "If SubjectAddress is not provided",
            "Fatal",
            "Subject",
            "Test GSE",
            "Governed test source",
            "../VALUATION_ANALYSIS/PROPERTIES/PROPERTY/",
        )
    )
    workbook.save(path)
    workbook.close()


def _write_configuration(path: Path, workbook_path: Path) -> None:
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
            Literal(WORKSHEET_NAME),
        )
    )
    graph.serialize(destination=path, format="turtle")


def _missing_subject_address_report() -> ET.Element:
    return ET.fromstring(
        f'''<MESSAGE xmlns="{MISMO}">
          <VALUATION_ANALYSIS>
            <PROPERTIES>
              <PROPERTY ValuationUseType="SubjectProperty" />
            </PROPERTIES>
          </VALUATION_ANALYSIS>
        </MESSAGE>'''
    )


def test_it_60_r3_s2_preserves_workbook_source_values_in_validation_findings(
    tmp_path: Path,
) -> None:
    workbook_path = tmp_path / "governed-compliance.xlsx"
    configuration_path = tmp_path / "configuration.ttl"
    _write_workbook(workbook_path)
    _write_configuration(configuration_path, workbook_path)

    investor = next(iter(Investor))
    try:
        findings = required_data.evaluate_required_data(
            _missing_subject_address_report(),
            investor,
            configuration_path=configuration_path,
        )
    except TypeError as error:
        raise AssertionError(
            "Required-data evaluation must accept the active workbook "
            "configuration and preserve its provenance in findings."
        ) from error

    finding = next(
        (
            item
            for item in findings
            if item.rule_id == "TEST-IT60-R3S2"
        ),
        None,
    )
    assert finding is not None, (
        "The missing SubjectAddress must produce a finding from the active "
        "workbook row."
    )
    assert finding.row_id == "0100.0007"
    assert finding.finding == (
        "Subject address is required by the governed workbook"
    )
    assert finding.source.source_document == str(workbook_path.resolve())
    assert getattr(finding.source, "source_sheet", None) == WORKSHEET_NAME, (
        "The finding provenance must identify the configured worksheet."
    )
