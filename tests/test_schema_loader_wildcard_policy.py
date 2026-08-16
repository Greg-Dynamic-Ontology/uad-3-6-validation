"""Acceptance tests for the documented UAD wildcard policy."""

from collections import Counter
from pathlib import Path

import pytest

from app.models.schema_model import SchemaModel
from app.services.schema_loader import SchemaLoader
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

WILDCARD_KINDS = frozenset({"any", "anyAttribute"})
GOVERNING_DECISION = "ADR-0014"


@pytest.fixture(scope="module")
def uad_schema_inventory() -> SchemaComponentInventory:
    """Inventory the official Combined UAD schema closure once."""

    documents = discover_schema_closure(COMBINED_SCHEMA_PATH)
    return inventory_schema_components(documents)


@pytest.fixture(scope="module")
def uad_schema_model() -> SchemaModel:
    """Load the official Combined UAD schema closure once for this suite."""

    return SchemaLoader().load(COMBINED_SCHEMA_PATH)


def test_every_wildcard_occurrence_receives_one_disposition(
    uad_schema_inventory: SchemaComponentInventory,
    uad_schema_model: SchemaModel,
) -> None:
    """IT-5R5S2: Each discovered wildcard has one stable disposition."""

    found_counts = Counter(
        occurrence.component_kind
        for occurrence in uad_schema_inventory.occurrences
        if occurrence.component_kind in WILDCARD_KINDS
    )
    dispositions = tuple(
        disposition
        for disposition in getattr(
            uad_schema_model,
            "processing_dispositions",
            (),
        )
        if disposition.component_kind in WILDCARD_KINDS
    )
    disposition_counts = Counter(
        disposition.component_kind
        for disposition in dispositions
    )
    occurrence_ids = {
        (
            disposition.source_document,
            disposition.source_index,
        )
        for disposition in dispositions
    }

    assert found_counts == {"any": 368, "anyAttribute": 1}
    assert disposition_counts == found_counts
    assert len(occurrence_ids) == sum(found_counts.values())


def test_wildcard_dispositions_identify_documented_ignore_policy(
    uad_schema_model: SchemaModel,
) -> None:
    """Every wildcard disposition names the action and governing ADR."""

    dispositions = tuple(
        disposition
        for disposition in getattr(
            uad_schema_model,
            "processing_dispositions",
            (),
        )
        if disposition.component_kind in WILDCARD_KINDS
    )

    assert dispositions
    assert all(
        disposition.action == "ignore"
        for disposition in dispositions
    )
    assert all(
        disposition.governing_decision == GOVERNING_DECISION
        for disposition in dispositions
    )


def test_ignored_wildcards_are_counted_as_processed(
    uad_schema_inventory: SchemaComponentInventory,
    uad_schema_model: SchemaModel,
) -> None:
    """Deliberate policy exclusion is processing, not an NP result."""

    found_counts = Counter(
        occurrence.component_kind
        for occurrence in uad_schema_inventory.occurrences
        if occurrence.component_kind in WILDCARD_KINDS
    )
    processed_counts = Counter(
        disposition.component_kind
        for disposition in getattr(
            uad_schema_model,
            "processing_dispositions",
            (),
        )
        if (
            disposition.component_kind in WILDCARD_KINDS
            and disposition.processed
        )
    )

    assert processed_counts == found_counts
