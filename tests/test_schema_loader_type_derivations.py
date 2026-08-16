"""Acceptance tests for UAD XML Schema type-derivation processing."""

from pathlib import Path

import pytest

from app.models.schema_model import QName, SchemaModel
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
XML_NAMESPACE = "http://www.w3.org/XML/1998/namespace"
XML_SCHEMA_NAMESPACE = "http://www.w3.org/2001/XMLSchema"


@pytest.fixture(scope="module")
def uad_schema_model() -> SchemaModel:
    """Load the official Combined UAD schema closure once for this suite."""

    assert COMBINED_SCHEMA_PATH.exists()
    return SchemaLoader().load(COMBINED_SCHEMA_PATH)


def test_named_simple_type_restriction_preserves_derivation(
    uad_schema_model: SchemaModel,
) -> None:
    """IT-5R3S2: A named restriction retains its method and base type."""

    access_base = uad_schema_model.simple_types[
        QName(MISMO_NAMESPACE, "AccessBase")
    ]

    assert getattr(access_base, "derivation_kind", None) == "restriction"
    assert access_base.base_type == QName(
        MISMO_NAMESPACE,
        "MISMOEnum_Base",
    )


def test_simple_content_extension_preserves_base_relationship(
    uad_schema_model: SchemaModel,
) -> None:
    """A simple-content extension retains its kind and base type."""

    access_enum = uad_schema_model.complex_types[
        QName(MISMO_NAMESPACE, "AccessEnum")
    ]

    assert getattr(access_enum, "simple_content", False) is True
    assert getattr(access_enum, "derivation_kind", None) == "extension"
    assert access_enum.base_type == QName(
        MISMO_NAMESPACE,
        "AccessBase",
    )


def test_simple_content_extension_preserves_extended_attributes(
    uad_schema_model: SchemaModel,
) -> None:
    """Attributes and attribute-group references added by an extension remain."""

    access_enum = uad_schema_model.complex_types[
        QName(MISMO_NAMESPACE, "AccessEnum")
    ]

    assert tuple(
        attribute.name.local_name
        for attribute in access_enum.attributes
        if attribute.name is not None
    ) == (
        "DataNotSuppliedReasonType",
        "DataNotSuppliedReasonTypeAdditionalDescription",
        "DataNotSuppliedReasonTypeOtherDescription",
        "SensitiveIndicator",
    )
    assert getattr(access_enum, "attribute_group_refs", None) == (
        QName(XLINK_NAMESPACE, "MISMOresourceLink"),
        QName(MISMO_NAMESPACE, "AttributeExtension"),
    )


def test_union_preserves_named_and_anonymous_members_in_order(
    uad_schema_model: SchemaModel,
) -> None:
    """The xml:lang union retains both member forms in declaration order."""

    xml_lang = uad_schema_model.attributes[
        QName(XML_NAMESPACE, "lang")
    ]
    inline_type = getattr(xml_lang, "inline_simple_type", None)

    assert inline_type is not None
    assert getattr(inline_type, "derivation_kind", None) == "union"

    union_members = getattr(inline_type, "union_members", None)

    assert union_members is not None
    assert len(union_members) == 2
    assert union_members[0] == QName(XML_SCHEMA_NAMESPACE, "language")

    anonymous_member = union_members[1]

    assert getattr(anonymous_member, "name", None) is None
    assert getattr(anonymous_member, "derivation_kind", None) == "restriction"
    assert getattr(anonymous_member, "base_type", None) == QName(
        XML_SCHEMA_NAMESPACE,
        "string",
    )
