"""Acceptance tests for UAD XML Schema datatype-facet processing."""

from pathlib import Path

import pytest

from app.models.schema_model import Facet, QName, SchemaModel
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

MISMO_NAMESPACE = "http://www.mismo.org/residential/2009/schemas"
XLINK_NAMESPACE = "http://www.w3.org/1999/xlink"


@pytest.fixture(scope="module")
def uad_schema_model() -> SchemaModel:
    """Load the official Combined UAD schema closure once for this suite."""

    assert COMBINED_SCHEMA_PATH.exists()
    return SchemaLoader().load(COMBINED_SCHEMA_PATH)


def test_enumeration_constraints_preserve_declared_order(
    uad_schema_model: SchemaModel,
) -> None:
    """IT-5R4S1: Enumeration values remain in declaration order."""

    access_base = uad_schema_model.simple_types[
        QName(MISMO_NAMESPACE, "AccessBase")
    ]

    assert access_base.enumeration_values == (
        "ExteriorAccessOnly",
        "InteriorAccessOnly",
        "InteriorAndExteriorAccess",
    )


def test_fraction_digits_constraint_is_preserved(
    uad_schema_model: SchemaModel,
) -> None:
    """A decimal restriction retains its fractionDigits constraint."""

    amount_base = uad_schema_model.simple_types[
        QName(MISMO_NAMESPACE, "MISMOAmount_Base")
    ]

    assert amount_base.facets == (
        Facet(name="fractionDigits", value="2"),
    )


def test_numeric_bounds_preserve_values_and_order(
    uad_schema_model: SchemaModel,
) -> None:
    """Minimum and maximum bounds retain lexical values and declaration order."""

    year_base = uad_schema_model.simple_types[
        QName(MISMO_NAMESPACE, "MISMOYear_Base")
    ]

    assert year_base.facets == (
        Facet(name="minInclusive", value="0001"),
        Facet(name="maxInclusive", value="9999"),
    )


def test_maximum_length_constraint_is_preserved(
    uad_schema_model: SchemaModel,
) -> None:
    """A string restriction retains its maxLength constraint."""

    code_base = uad_schema_model.simple_types[
        QName(MISMO_NAMESPACE, "MISMOCode_Base")
    ]

    assert code_base.facets == (
        Facet(name="maxLength", value="16383"),
    )


def test_minimum_length_constraint_is_preserved(
    uad_schema_model: SchemaModel,
) -> None:
    """An imported XLink restriction retains its minLength constraint."""

    role_type = uad_schema_model.simple_types[
        QName(XLINK_NAMESPACE, "roleType")
    ]

    assert role_type.facets == (
        Facet(name="minLength", value="1"),
    )


def test_pattern_constraint_is_preserved_verbatim(
    uad_schema_model: SchemaModel,
) -> None:
    """A pattern retains the exact regular-expression lexical value."""

    date_base = uad_schema_model.simple_types[
        QName(MISMO_NAMESPACE, "MISMODate_Base")
    ]

    assert date_base.facets == (
        Facet(
            name="pattern",
            value=r"[0-9]{4}([\-][0-9]{2}){0,2}",
        ),
    )
