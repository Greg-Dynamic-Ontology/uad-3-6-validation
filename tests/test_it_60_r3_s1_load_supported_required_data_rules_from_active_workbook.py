"""IT-60R3S1: load supported required-data rules from the active workbook."""

from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook
from rdflib import Graph, Literal, Namespace, RDF

from app.services import required_data


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


def _write_workbook(path: Path) -> None:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Governed rules"
    worksheet.append(CONSTRAINT_HEADERS)
    worksheet.append(
        (
            "0100.0007",
            "SubjectAddress",
            "TEST-IT60-R3S1",
            "Subject address is required",
            "If SubjectAddress is not provided",
            "Fatal",
            "Subject",
            "GSE",
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
            Literal("Governed rules"),
        )
    )
    graph.serialize(destination=path, format="turtle")


def test_it_60_r3_s1_loads_supported_required_data_rules_from_active_workbook(
    tmp_path: Path,
    monkeypatch,
) -> None:
    workbook_path = tmp_path / "governed-compliance.xlsx"
    configuration_path = tmp_path / "configuration.ttl"
    _write_workbook(workbook_path)
    _write_configuration(configuration_path, workbook_path)

    # Production loading must use the configured workbook, not fall back to
    # the legacy CSV source even if that path is unavailable.
    monkeypatch.setattr(
        required_data,
        "RULE_FILE",
        tmp_path / "legacy-csv-must-not-be-read.csv",
        raising=False,
    )
    required_data.load_required_rules.cache_clear()
    try:
        try:
            rules = required_data.load_required_rules(
                configuration_path=configuration_path,
            )
        except TypeError as error:
            raise AssertionError(
                "The production required-data loader must accept the active "
                "configuration and load workbook-derived rows."
            ) from error
    finally:
        required_data.load_required_rules.cache_clear()

    matching_rules = [
        rule
        for rule in rules
        if rule.get("Message ID") == "TEST-IT60-R3S1"
    ]
    assert len(matching_rules) == 1, (
        "The supported required-data rule from the active workbook must be "
        "loaded exactly once."
    )
    assert matching_rules[0]["Unique ID"] == "0100.0007"
    assert matching_rules[0]["Primary Data Element"] == "SubjectAddress"
