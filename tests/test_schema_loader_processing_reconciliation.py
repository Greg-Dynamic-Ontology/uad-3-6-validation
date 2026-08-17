"""Acceptance tests for IT-5R7S1 processing reconciliation."""

from collections import Counter
from pathlib import Path

import pytest

from app.models.schema_model import SchemaModel
from app.services.schema_loader import SchemaLoader
from app.services.schema_loader.processing_coverage import (
    report_component_processing_coverage,
)
from app.services.schema_loader.schema_closure import (
    SchemaComponentInventory,
    discover_schema_closure,
    inventory_schema_components,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
COMBINED_SCHEMA_PATH = (
    PROJECT_ROOT
    / "specs"
    / "UAD"
    / "GSE_UAD_3.6.0_v1.3"
    / "Combined"
    / "GSE_UAD_3.6.0_v1.3.xsd"
)
ALLOWED_ACTIONS = frozenset(
    {
        "represent",
        "ignore",
        "not_processed",
    }
)


@pytest.fixture(scope="module")
def uad_schema_inventory() -> SchemaComponentInventory:
    """Inventory the official Combined UAD schema closure once."""

    documents = discover_schema_closure(COMBINED_SCHEMA_PATH)
    return inventory_schema_components(documents)


@pytest.fixture(scope="module")
def uad_schema_model() -> SchemaModel:
    """Process the official Combined UAD schema closure once."""

    return SchemaLoader().load(COMBINED_SCHEMA_PATH)


def test_every_discovered_occurrence_has_exactly_one_disposition(
    uad_schema_inventory: SchemaComponentInventory,
    uad_schema_model: SchemaModel,
) -> None:
    """Reconcile dispositions by source document and source index."""

    occurrences = uad_schema_inventory.occurrences
    dispositions = uad_schema_model.processing_dispositions

    assert len(dispositions) == len(occurrences)

    occurrence_ids = Counter(
        (
            occurrence.source_document.resolve(),
            occurrence.source_index,
            occurrence.component_kind,
        )
        for occurrence in occurrences
    )
    disposition_ids = Counter(
        (
            disposition.source_document.resolve(),
            disposition.source_index,
            disposition.component_kind,
        )
        for disposition in dispositions
    )

    assert disposition_ids == occurrence_ids
    assert all(count == 1 for count in disposition_ids.values())


def test_each_disposition_has_one_deliberate_outcome(
    uad_schema_model: SchemaModel,
) -> None:
    """Allow representation, documented exclusion, or explicit NP."""

    for disposition in uad_schema_model.processing_dispositions:
        assert disposition.action in ALLOWED_ACTIONS

        if disposition.action == "represent":
            assert disposition.processed is True
        elif disposition.action == "ignore":
            assert disposition.processed is True
            assert disposition.governing_decision.startswith("ADR-")
        else:
            assert disposition.processed is False


def test_found_and_disposition_counts_reconcile_without_incomplete_kinds(
    uad_schema_inventory: SchemaComponentInventory,
    uad_schema_model: SchemaModel,
) -> None:
    """Reconcile all 24 kinds without leaving a partial disposition set."""

    disposition_counts = Counter(
        disposition.component_kind
        for disposition in uad_schema_model.processing_dispositions
    )

    assert dict(disposition_counts) == dict(
        uad_schema_inventory.counts_by_kind
    )

    report = report_component_processing_coverage(uad_schema_model)
    assert all(
        row.status not in {"NP", "Incomplete"}
        for row in report.component_kinds
    )
