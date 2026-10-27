"""IT-62R3S2: reject incomplete or ambiguous workbook source definitions."""

from uuid import uuid4

import pytest
from rdflib import Graph, Literal, Namespace, RDF
from rdflib.compare import isomorphic

from app.services.configuration_knowledge import validate_workbook_source_definition


CFG = Namespace("https://dynamicontology.com/uad36/configuration#")


@pytest.mark.parametrize(
    "definition, invalid_property, expected_count",
    [
        ("no-rule-data-worksheet", CFG.ruleDataSheetName, 0),
        ("multiple-rule-data-sheets", CFG.ruleDataSheetName, 2),
        ("no-source-file-location", CFG.sourceFileLocation, 0),
    ],
    ids=[
        "missing-rule-data-worksheet",
        "ambiguous-rule-data-worksheet",
        "missing-workbook-location",
    ],
)
def test_it_62_r3_s2_rejects_incomplete_or_ambiguous_workbook_source(
    definition: str, invalid_property, expected_count: int,
) -> None:
    token = uuid4().hex
    workbook = CFG[f"workbook-{token}"]
    other_workbook = CFG[f"other-workbook-{token}"]
    configuration = Graph()
    configuration.add((workbook, RDF.type, CFG.GovernedSourceArtifact))

    if definition != "no-source-file-location":
        configuration.add((
            workbook, CFG.sourceFileLocation,
            Literal(r"C:\governed sources\compliance-rules.xlsx"),
        ))
    if definition != "no-rule-data-worksheet":
        configuration.add((workbook, CFG.ruleDataSheetName, Literal("Governed rules")))
    if definition == "multiple-rule-data-sheets":
        configuration.add((workbook, CFG.ruleDataSheetName, Literal("Alternate rules")))

    # Descriptive tabs must not substitute for an explicit rule-data selection.
    configuration.add((workbook, CFG.sourceSheetName, Literal("Governed rules")))
    configuration.add((workbook, CFG.sourceSheetName, Literal("Read Me")))

    # Another workbook's complete definition must not repair this one.
    configuration.add((other_workbook, RDF.type, CFG.GovernedSourceArtifact))
    configuration.add((other_workbook, CFG.sourceFileLocation, Literal("other.xlsx")))
    configuration.add((other_workbook, CFG.ruleDataSheetName, Literal("Other rules")))

    original = Graph()
    for triple in configuration:
        original.add(triple)

    result = validate_workbook_source_definition(
        configuration_graph=configuration, workbook_id=workbook,
    )

    assert result.conforms is False, (
        f"IT-62R3S2 requires rejection of {definition}."
    )
    assert result.workbook_id == workbook
    diagnostics = tuple(result.diagnostics)
    assert diagnostics and all(
        isinstance(message, str) and message.strip() for message in diagnostics
    ), "Rejection must explain the incomplete or ambiguous source definition."
    diagnostic = "\n".join(diagnostics)
    assert str(workbook) in diagnostic
    assert str(invalid_property) in diagnostic, (
        "The diagnostic must identify the missing or ambiguous configuration property."
    )
    if expected_count == 2:
        assert "exactly one" in diagnostic.casefold(), (
            "The diagnostic must explain that exactly one rule-data worksheet is required."
        )
    else:
        assert any(word in diagnostic.casefold() for word in ("missing", "required", "exactly one")), (
            "The diagnostic must explain that the absent value is required."
        )

    if invalid_property == CFG.ruleDataSheetName:
        assert result.rule_data_sheet_name is None, (
            "Validation must not invent or choose a worksheet for an invalid definition."
        )
    else:
        assert result.source_file_location is None, (
            "Validation must not invent a missing workbook location."
        )
    assert isomorphic(configuration, original), (
        "Rejection must not silently repair or change the configuration RDF."
    )
