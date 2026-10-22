"""Reconcile UAD1535 with the configured published compliance workbook."""

from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from app.models.enums import Investor
from app.services import uniqueness_cardinality_required_data as service
from app.services.gse_constraint_sources import (
    read_active_compliance_workbook_rows,
)


ROOT = Path(__file__).resolve().parents[1]
NS = "http://www.mismo.org/residential/2009/schemas"
XLINK = "http://www.w3.org/1999/xlink"
SIGNATORY_ROLE = (
    "urn:fdc:mismo.org:2009:residential/"
    "SIGNATORY_IsAssociatedWith_ROLE"
)


@pytest.fixture(scope="module")
def governed_row():
    source = read_active_compliance_workbook_rows(
        configuration_path=ROOT / "config" / "configuration.ttl",
    )
    matches = [
        dict(row)
        for row in source.rows
        if row.get("Message ID") == "UAD1535"
    ]
    assert len(matches) == 1, (
        "The configured workbook must contain exactly one UAD1535 row."
    )
    row = matches[0]
    row["_source_document"] = str(source.workbook_path)
    row["_source_sheet"] = source.worksheet_name
    return row


def element(parent, name, text=None):
    node = ET.SubElement(parent, f"{{{NS}}}{name}")
    if text is not None:
        node.text = text
    return node


def add_document(documents, parties_spec):
    """Build an evaluator fragment with actual signature-role relationships.

    Each specification is (role_type, signature_counts).
    Each count creates one linked SIGNATORY:
      0 or greater: that many ExecutionDate elements
      -1: no EXECUTION
      -2: EXECUTION without EXECUTION_DETAIL
    An empty signature_counts tuple creates no signature for that party.
    """
    document = element(documents, "DOCUMENT")
    deal_sets = element(document, "DEAL_SETS")
    deal_set = element(deal_sets, "DEAL_SET")
    deals = element(deal_set, "DEALS")
    deal = element(deals, "DEAL")
    services = element(deal, "SERVICES")
    valuation_service = element(services, "SERVICE")
    parties = element(valuation_service, "PARTIES")
    relationships = element(valuation_service, "RELATIONSHIPS")
    signatories = element(document, "SIGNATORIES")

    for party_index, (role_type, counts) in enumerate(parties_spec):
        party = element(parties, "PARTY")
        roles = element(party, "ROLES")
        role = element(roles, "ROLE")
        role_label = f"ROLE_{party_index}"
        role.set(f"{{{XLINK}}}label", role_label)
        detail = element(role, "ROLE_DETAIL")
        element(detail, "PartyRoleType", role_type)

        for signature_index, count in enumerate(counts):
            signature_label = f"SIGNATORY_{party_index}_{signature_index}"
            signature = element(signatories, "SIGNATORY")
            signature.set(f"{{{XLINK}}}label", signature_label)

            relationship = element(relationships, "RELATIONSHIP")
            relationship.set(f"{{{XLINK}}}arcrole", SIGNATORY_ROLE)
            relationship.set(f"{{{XLINK}}}from", signature_label)
            relationship.set(f"{{{XLINK}}}to", role_label)

            if count == -1:
                continue
            execution = element(signature, "EXECUTION")
            if count == -2:
                continue
            execution_detail = element(execution, "EXECUTION_DETAIL")
            for _ in range(count):
                element(execution_detail, "ExecutionDate", "2026-10-01")

    return document


def report(*document_specs):
    """These are evaluator fragments, not complete schema-valid reports."""
    root = ET.Element(f"{{{NS}}}MESSAGE")
    document_sets = element(root, "DOCUMENT_SETS")
    document_set = element(document_sets, "DOCUMENT_SET")
    documents = element(document_set, "DOCUMENTS")
    for specification in document_specs:
        add_document(documents, specification)
    return root


def evaluate(root, governed_row):
    return service.evaluate_uniqueness_cardinality(
        root,
        Investor.FANNIE_MAE,
        governed_row,
    )


@pytest.mark.parametrize(
    "parties_spec,expected_count",
    [
        ([("Appraiser", (1,))], 0),
        ([("Appraiser", (0,))], 1),
        ([("Appraiser", (2,))], 1),
        ([("Appraiser", (-1,))], 1),
        ([("Appraiser", (-2,))], 1),
        ([("Appraiser", ())], 1),
        (
            [("Appraiser", (1,)), ("AppraiserSupervisor", (1,))],
            0,
        ),
        (
            [("Appraiser", (1,)), ("AppraiserSupervisor", (0,))],
            1,
        ),
        ([("Borrower", (0,))], 0),
        ([("Appraiser", (1, 1))], 1),
        ([("Appraiser", (1,)), ("Appraiser", (1,))], 0),
    ],
    ids=[
        "one-appraiser-date",
        "missing-date",
        "duplicate-dates",
        "missing-execution",
        "missing-execution-detail",
        "missing-signatory",
        "appraiser-and-supervisor-valid",
        "supervisor-missing-date",
        "unrelated-party-role",
        "duplicate-dates-across-signatories-for-one-party",
        "separate-appraiser-parties",
    ],
)
def test_uad1535_requires_one_date_per_applicable_party(
    governed_row,
    parties_spec,
    expected_count,
):
    findings = evaluate(report(parties_spec), governed_row)
    assert len(findings) == expected_count
    for finding in findings:
        assert finding.rule_id == governed_row["Message ID"]
        assert finding.row_id == governed_row["Unique ID"]
        assert finding.expected_condition == governed_row["Rule Logic"]
        assert finding.finding == governed_row["Message Text"]


def test_uad1535_isolates_documents(governed_row):
    root = report(
        [("Appraiser", (0,))],
        [("Appraiser", (1,))],
    )
    # Labels deliberately repeat between documents. A date in the second
    # document must not satisfy the first document's appraiser.
    findings = evaluate(root, governed_row)
    assert len(findings) == 1


def test_uad1535_preserves_workbook_provenance(governed_row):
    findings = evaluate(report([("Appraiser", (0,))]), governed_row)
    assert len(findings) == 1
    finding = findings[0]
    assert finding.source.source_document == governed_row["_source_document"]
    assert finding.source.source_sheet == governed_row["_source_sheet"]


def test_uad1535_rejects_unreviewed_source_changes(governed_row):
    changed = dict(governed_row)
    changed["Rule Logic"] += " Unreviewed change."
    with pytest.raises(
        ValueError,
        match="UAD1535: governed uniqueness/cardinality definition changed",
    ):
        service.binding_for(changed)