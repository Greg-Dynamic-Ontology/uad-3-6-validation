"""IT-62R2S1: accept exactly one active workbook in the configured collection."""

from importlib import import_module
from uuid import uuid4

import pytest
from rdflib import Graph, Literal, Namespace, RDF
from rdflib.compare import isomorphic


CFG = Namespace("https://dynamicontology.com/uad36/configuration#")


@pytest.mark.parametrize("selected_index", [0, 1], ids=["fannie-mae", "freddie-mac"])
def test_it_62_r2_s1_accepts_one_active_workbook_from_available_collection(
    selected_index: int,
) -> None:
    token = uuid4().hex
    configuration_id = CFG[f"configuration-{token}"]
    collection = CFG[f"source-workbooks-{token}"]
    workbooks = (
        CFG[f"fannie-mae-{token}"],
        CFG[f"freddie-mac-{token}"],
    )
    selected = workbooks[selected_index]
    configuration = Graph()
    configuration.add((configuration_id, RDF.type, CFG.ApplicationConfiguration))
    configuration.add((configuration_id, CFG.hasSourceWorkbooks, collection))
    configuration.add((collection, RDF.type, CFG.GovernedSourceWorkbookCollection))
    for workbook in workbooks:
        configuration.add((collection, CFG.containsWorkbook, workbook))
        configuration.add((workbook, RDF.type, CFG.GovernedSourceArtifact))
        configuration.add((workbook, CFG.ruleDataSheetName, Literal("Governed rules")))
    configuration.add((configuration_id, CFG.activeComplianceSource, selected))

    original = Graph()
    for triple in configuration:
        original.add(triple)

    operation = getattr(
        import_module("app.services.configuration_knowledge"),
        "validate_active_compliance_source",
        None,
    )
    assert callable(operation), (
        "IT-62R2S1 requires validate_active_compliance_source("
        "configuration_graph=..., configuration_id=...) to validate exactly "
        "one active workbook against the configuration's source collection. "
        "Vocabulary coverage alone does not validate source selection."
    )

    result = operation(
        configuration_graph=configuration,
        configuration_id=configuration_id,
    )

    assert result.conforms is True, (
        "One active workbook belonging to the available source collection "
        "must be accepted, even when other workbooks remain available."
    )
    assert result.active_source == selected, (
        "Acceptance must preserve the exact selected governed workbook identity."
    )
    assert tuple(result.diagnostics) == (), (
        "A valid active-source selection must have no rejection diagnostics."
    )
    assert isomorphic(configuration, original), (
        "Validating source selection must not alter configuration knowledge."
    )
