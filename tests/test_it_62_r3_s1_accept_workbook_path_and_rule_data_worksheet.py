"""IT-62R3S1: accept an explicit workbook location and rule-data worksheet."""

from importlib import import_module
from uuid import uuid4

import pytest
from rdflib import Graph, Literal, Namespace, RDF
from rdflib.compare import isomorphic


CFG = Namespace("https://dynamicontology.com/uad36/configuration#")


@pytest.mark.parametrize(
    "location, worksheet",
    [
        (
            r"C:\governed sources\Fannie Mae\Compliance Rules.xlsm",
            "UAD Compliance Rules v1.5",
        ),
        (
            r"C:\governed sources\Freddie Mac\compliance-rules.xlsx",
            "Governed rule data",
        ),
    ],
    ids=["fannie-mae", "freddie-mac"],
)
def test_it_62_r3_s1_accepts_workbook_with_one_path_and_rule_data_worksheet(
    location: str, worksheet: str,
) -> None:
    token = uuid4().hex
    workbook = CFG[f"workbook-{token}"]
    other_workbook = CFG[f"other-workbook-{token}"]
    configuration = Graph()
    configuration.add((workbook, RDF.type, CFG.GovernedSourceArtifact))
    configuration.add((workbook, CFG.sourceFileLocation, Literal(location)))
    configuration.add((workbook, CFG.ruleDataSheetName, Literal(worksheet)))

    # Other tabs describe the workbook but are not rule-data selections.
    configuration.add((workbook, CFG.sourceSheetName, Literal("Read Me")))
    configuration.add((workbook, CFG.sourceSheetName, Literal(worksheet)))
    configuration.add((workbook, CFG.sourceSheetName, Literal("Column Description")))

    # Definitions on other resources must not count toward this workbook.
    configuration.add((other_workbook, RDF.type, CFG.GovernedSourceArtifact))
    configuration.add((other_workbook, CFG.sourceFileLocation, Literal("other.xlsx")))
    configuration.add((other_workbook, CFG.ruleDataSheetName, Literal("Other rules")))

    original = Graph()
    for triple in configuration:
        original.add(triple)

    operation = getattr(
        import_module("app.services.configuration_knowledge"),
        "validate_workbook_source_definition",
        None,
    )
    assert callable(operation), (
        "IT-62R3S1 requires validate_workbook_source_definition("
        "configuration_graph=..., workbook_id=...) to validate a configured "
        "workbook's source file location and rule-data worksheet name."
    )

    result = operation(configuration_graph=configuration, workbook_id=workbook)

    assert result.conforms is True, (
        "A workbook with one explicit source location and one rule-data "
        "worksheet name must be accepted."
    )
    assert result.workbook_id == workbook
    assert result.source_file_location == location
    assert result.rule_data_sheet_name == worksheet, (
        "The configured rule-data worksheet must be preserved exactly; "
        "other sourceSheetName values must not replace it."
    )
    assert tuple(result.diagnostics) == ()
    assert isomorphic(configuration, original), (
        "Validating a workbook source definition must not change its RDF."
    )
