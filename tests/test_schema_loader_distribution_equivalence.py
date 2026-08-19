"""Acceptance tests for IT-5R7S2 schema-distribution equivalence."""

from collections import Counter
from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from enum import Enum
from pathlib import Path

import pytest

from app.models.schema_model import SchemaModel
from app.services.schema_loader import SchemaLoader
from app.services.schema_loader.processing_coverage import (
    report_component_processing_coverage,
)
from app.services.schema_loader.schema_closure import (
    SchemaComponentInventory,
    SchemaDocument,
    discover_schema_closure,
    inventory_schema_components,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
UAD_SCHEMA_DIRECTORY = (
    PROJECT_ROOT / "specs" / "UAD" / "GSE_UAD_3.6.0_v1.3"
)
COMBINED_DIRECTORY = UAD_SCHEMA_DIRECTORY / "Combined"
INDIVIDUAL_DIRECTORY = UAD_SCHEMA_DIRECTORY / "Individual"
ENTRY_POINT_NAME = "GSE_UAD_3.6.0_v1.3.xsd"
COMBINED_ENTRY_POINT = COMBINED_DIRECTORY / ENTRY_POINT_NAME
INDIVIDUAL_ENTRY_POINT = INDIVIDUAL_DIRECTORY / ENTRY_POINT_NAME


@pytest.fixture(scope="module")
def combined_documents() -> tuple[SchemaDocument, ...]:
    return discover_schema_closure(COMBINED_ENTRY_POINT)


@pytest.fixture(scope="module")
def individual_documents() -> tuple[SchemaDocument, ...]:
    return discover_schema_closure(INDIVIDUAL_ENTRY_POINT)


@pytest.fixture(scope="module")
def combined_model() -> SchemaModel:
    return SchemaLoader().load(COMBINED_ENTRY_POINT)


@pytest.fixture(scope="module")
def individual_model() -> SchemaModel:
    return SchemaLoader().load(INDIVIDUAL_ENTRY_POINT)


def test_each_distribution_discovers_its_complete_schema_closure(
    combined_documents: tuple[SchemaDocument, ...],
    individual_documents: tuple[SchemaDocument, ...],
) -> None:
    """Follow every import and include once in each distribution."""

    combined_paths = {
        document.path.resolve()
        for document in combined_documents
    }
    individual_paths = {
        document.path.resolve()
        for document in individual_documents
    }

    assert combined_paths == {
        path.resolve()
        for path in COMBINED_DIRECTORY.glob("*.xsd")
    }
    assert individual_paths == {
        path.resolve()
        for path in INDIVIDUAL_DIRECTORY.glob("*.xsd")
    }
    assert len(combined_paths) == len(combined_documents)
    assert len(individual_paths) == len(individual_documents)


def test_combined_and_individual_logical_models_are_equivalent(
    combined_model: SchemaModel,
    individual_model: SchemaModel,
) -> None:
    """Ignore packaging metadata while comparing logical schema meaning."""

    assert _logical_content(individual_model) == _logical_content(
        combined_model
    )


@pytest.mark.parametrize(
    ("documents_fixture", "model_fixture"),
    (
        ("combined_documents", "combined_model"),
        ("individual_documents", "individual_model"),
    ),
)
def test_distribution_coverage_reconciles_to_its_schema_closure(
    documents_fixture: str,
    model_fixture: str,
    request: pytest.FixtureRequest,
) -> None:
    """Reconcile each physical closure independently and completely."""

    documents = request.getfixturevalue(documents_fixture)
    model = request.getfixturevalue(model_fixture)
    inventory = inventory_schema_components(documents)

    _assert_complete_reconciliation(inventory, model)


def _logical_content(schema: SchemaModel) -> tuple[object, ...]:
    """Return structural meaning without packaging or documentation."""

    return _canonicalize(
        (
            schema.target_namespace,
            schema.elements,
            schema.complex_types,
            schema.simple_types,
            schema.attributes,
            schema.attribute_groups,
            schema.model_groups,
            schema.namespaces,
        )
    )


def _canonicalize(value: object) -> object:
    """Canonicalize structural content for deterministic comparison."""

    if is_dataclass(value) and not isinstance(value, type):
        return tuple(
            (
                field.name,
                _canonicalize(getattr(value, field.name)),
            )
            for field in fields(value)
            if field.name != "documentation"
            and field.metadata.get("logical_schema", True)
        )

    if isinstance(value, Mapping):
        entries = (
            (_canonicalize(key), _canonicalize(item))
            for key, item in value.items()
        )
        return tuple(sorted(entries, key=repr))

    if isinstance(value, (set, frozenset)):
        return tuple(
            sorted(
                (_canonicalize(item) for item in value),
                key=repr,
            )
        )

    if isinstance(value, (list, tuple)):
        return tuple(_canonicalize(item) for item in value)

    if isinstance(value, Enum):
        return value.value

    return value


def _assert_complete_reconciliation(
    inventory: SchemaComponentInventory,
    model: SchemaModel,
) -> None:
    occurrence_ids = Counter(
        (
            occurrence.source_document.resolve(),
            occurrence.source_index,
            occurrence.component_kind,
        )
        for occurrence in inventory.occurrences
    )
    disposition_ids = Counter(
        (
            disposition.source_document.resolve(),
            disposition.source_index,
            disposition.component_kind,
        )
        for disposition in model.processing_dispositions
    )

    assert disposition_ids == occurrence_ids
    assert dict(model.component_counts) == dict(inventory.counts_by_kind)

    report = report_component_processing_coverage(model)
    report_counts = {
        row.component_kind: (row.found, row.processed)
        for row in report.component_kinds
    }
    assert report_counts == {
        component_kind: (found, found)
        for component_kind, found in inventory.counts_by_kind.items()
    }
    assert all(
        row.status == "Processed"
        for row in report.component_kinds
    )
