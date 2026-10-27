"""IT-62R2S2: reject absent, unlisted, or multiple active workbooks."""

from uuid import uuid4

import pytest
from rdflib import Graph, Namespace, RDF
from rdflib.compare import isomorphic

from app.services.configuration_knowledge import validate_active_compliance_source


CFG = Namespace("https://dynamicontology.com/uad36/configuration#")


@pytest.mark.parametrize(
    "selection",
    ["absent", "outside-collection", "multiple-workbooks"],
)
def test_it_62_r2_s2_rejects_invalid_active_workbook_selection(
    selection: str,
) -> None:
    token = uuid4().hex
    configuration_id = CFG[f"configuration-{token}"]
    collection = CFG[f"source-workbooks-{token}"]
    fannie = CFG[f"fannie-mae-{token}"]
    freddie = CFG[f"freddie-mac-{token}"]
    outside = CFG[f"unlisted-workbook-{token}"]
    configuration = Graph()
    configuration.add((configuration_id, RDF.type, CFG.ApplicationConfiguration))
    configuration.add((configuration_id, CFG.hasSourceWorkbooks, collection))
    configuration.add((collection, RDF.type, CFG.GovernedSourceWorkbookCollection))
    for workbook in (fannie, freddie):
        configuration.add((collection, CFG.containsWorkbook, workbook))
        configuration.add((workbook, RDF.type, CFG.GovernedSourceArtifact))

    if selection == "outside-collection":
        # Being described as a workbook does not make it a collection member.
        configuration.add((outside, RDF.type, CFG.GovernedSourceArtifact))
        configuration.add((configuration_id, CFG.activeComplianceSource, outside))
    elif selection == "multiple-workbooks":
        for workbook in (fannie, freddie):
            configuration.add((configuration_id, CFG.activeComplianceSource, workbook))

    original = Graph()
    for triple in configuration:
        original.add(triple)

    result = validate_active_compliance_source(
        configuration_graph=configuration,
        configuration_id=configuration_id,
    )

    assert result.conforms is False, (
        f"IT-62R2S2 requires rejection of {selection} active-source selection."
    )
    assert result.active_source is None, (
        "An invalid selection must not return an accepted or default workbook."
    )
    diagnostics = tuple(result.diagnostics)
    assert diagnostics and all(
        isinstance(message, str) and message.strip() for message in diagnostics
    ), "Rejection must explain the invalid source selection."
    diagnostic = "\n".join(diagnostics)
    assert str(configuration_id) in diagnostic

    if selection == "outside-collection":
        assert str(outside) in diagnostic
        assert str(collection) in diagnostic
        assert "listed" in diagnostic.casefold(), (
            "The diagnostic must explain that the active source must be listed."
        )
    else:
        assert "active" in diagnostic.casefold()
        assert "exactly one" in diagnostic.casefold(), (
            "The diagnostic must explain that exactly one active source is required."
        )

    assert isomorphic(configuration, original), (
        "Rejection must not silently repair or alter configuration knowledge."
    )
