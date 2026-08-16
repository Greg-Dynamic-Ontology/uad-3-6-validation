"""Acceptance tests for UAD XML Schema model-group processing."""

from pathlib import Path

import pytest

from app.models.schema_model import ModelGroupKind, QName, SchemaModel
from app.services.schema_loader import SchemaLoader


PROJECT_ROOT = Path(__file__).resolve().parents[1]
COMBINED_SCHEMA_PATH = (
    PROJECT_ROOT
    / "specs"
    / "UAD"
    / "GSE_UAD_3.6.0_v1.3"
    / "Combined"
    / "GSE_UAD_3.6.0_v1.3.xsd"
)

XLINK_NAMESPACE = "http://www.w3.org/1999/xlink"


@pytest.fixture(scope="module")
def uad_schema_model() -> SchemaModel:
    """Load the official Combined UAD schema closure once for this suite."""

    assert COMBINED_SCHEMA_PATH.exists()
    return SchemaLoader().load(COMBINED_SCHEMA_PATH)


def test_uad_named_model_groups_are_represented(
    uad_schema_model: SchemaModel,
) -> None:
    """IT-5R3S1: Every named XLink model group is indexed by QName."""

    model_groups = getattr(uad_schema_model, "model_groups", None)

    assert model_groups is not None, (
        "SchemaModel must represent named XML Schema model groups."
    )
    assert set(model_groups) == {
        QName(XLINK_NAMESPACE, "simpleModel"),
        QName(XLINK_NAMESPACE, "extendedModel"),
        QName(XLINK_NAMESPACE, "titleModel"),
        QName(XLINK_NAMESPACE, "resourceModel"),
        QName(XLINK_NAMESPACE, "locatorModel"),
        QName(XLINK_NAMESPACE, "arcModel"),
    }


def test_choice_preserves_ordered_element_references(
    uad_schema_model: SchemaModel,
) -> None:
    """A choice retains the order of its child element references."""

    model_groups = getattr(uad_schema_model, "model_groups", {})
    extended_model = model_groups[
        QName(XLINK_NAMESPACE, "extendedModel")
    ]

    assert extended_model.kind is ModelGroupKind.CHOICE
    assert tuple(element.ref for element in extended_model.elements) == (
        QName(XLINK_NAMESPACE, "title"),
        QName(XLINK_NAMESPACE, "resource"),
        QName(XLINK_NAMESPACE, "locator"),
        QName(XLINK_NAMESPACE, "arc"),
    )
    assert extended_model.min_occurs == 1
    assert extended_model.max_occurs == 1


def test_sequence_preserves_element_reference_occurrence_constraints(
    uad_schema_model: SchemaModel,
) -> None:
    """An element reference retains its position and occurrence bounds."""

    model_groups = getattr(uad_schema_model, "model_groups", {})
    locator_model = model_groups[
        QName(XLINK_NAMESPACE, "locatorModel")
    ]

    assert locator_model.kind is ModelGroupKind.SEQUENCE
    assert len(locator_model.elements) == 1

    title_reference = locator_model.elements[0]

    assert title_reference.name is None
    assert title_reference.ref == QName(XLINK_NAMESPACE, "title")
    assert title_reference.min_occurs == 0
    assert title_reference.max_occurs is None


def test_complex_type_preserves_group_reference_and_occurrences(
    uad_schema_model: SchemaModel,
) -> None:
    """A complex type retains its named group reference and use bounds."""

    extended_type = uad_schema_model.complex_types[
        QName(XLINK_NAMESPACE, "extended")
    ]

    assert extended_type.content is not None
    assert getattr(extended_type.content, "ref", None) == QName(
        XLINK_NAMESPACE,
        "extendedModel",
    )
    assert extended_type.content.min_occurs == 0
    assert extended_type.content.max_occurs is None


def test_existing_direct_sequence_order_remains_preserved(
    uad_schema_model: SchemaModel,
) -> None:
    """Direct UAD sequences continue to preserve declaration order."""

    mismo_namespace = "http://www.mismo.org/residential/2009/schemas"
    about_version = uad_schema_model.complex_types[
        QName(mismo_namespace, "ABOUT_VERSION")
    ]

    assert about_version.content is not None
    assert about_version.content.kind is ModelGroupKind.SEQUENCE
    assert tuple(
        element.name.local_name
        for element in about_version.content.elements
        if element.name is not None
    ) == (
        "AboutVersionIdentifier",
        "EXTENSION",
    )
