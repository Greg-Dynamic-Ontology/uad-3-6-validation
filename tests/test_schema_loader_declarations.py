"""Acceptance tests for UAD XML Schema declaration processing."""

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


def test_uad_global_declarations_are_represented(
    uad_schema_model: SchemaModel,
) -> None:
    """IT-5R2S1: Global UAD declarations are indexed by QName."""

    actual_counts = {
        "elements": len(uad_schema_model.elements),
        "attributes": len(uad_schema_model.attributes),
        "attribute_groups": len(uad_schema_model.attribute_groups),
        "complex_types": len(uad_schema_model.complex_types),
        "named_simple_types": len(uad_schema_model.simple_types),
    }

    assert actual_counts == {
        "elements": 5,
        "attributes": 14,
        "attribute_groups": 10,
        "complex_types": 1297,
        "named_simple_types": 221,
    }


def test_global_element_and_attribute_type_relationships_are_preserved(
    uad_schema_model: SchemaModel,
) -> None:
    """Global element and attribute declarations retain their type QNames."""

    message_name = QName(MISMO_NAMESPACE, "MESSAGE")
    xlink_title_name = QName(XLINK_NAMESPACE, "title")
    xlink_type_name = QName(XLINK_NAMESPACE, "type")
    xml_base_name = QName(XML_NAMESPACE, "base")

    assert uad_schema_model.elements[message_name].type_name == QName(
        MISMO_NAMESPACE,
        "MESSAGE",
    )
    assert uad_schema_model.elements[xlink_title_name].type_name == QName(
        XLINK_NAMESPACE,
        "titleEltType",
    )
    assert uad_schema_model.attributes[xlink_type_name].type_name == QName(
        XLINK_NAMESPACE,
        "typeType",
    )
    assert uad_schema_model.attributes[xml_base_name].type_name == QName(
        XML_SCHEMA_NAMESPACE,
        "anyURI",
    )


def test_attribute_group_memberships_are_preserved(
    uad_schema_model: SchemaModel,
) -> None:
    """Attribute groups retain ordered references to global attributes."""

    special_attributes = uad_schema_model.attribute_groups[
        QName(XML_NAMESPACE, "specialAttrs")
    ]
    simple_attributes = uad_schema_model.attribute_groups[
        QName(XLINK_NAMESPACE, "simpleAttrs")
    ]

    assert tuple(
        attribute.ref
        for attribute in special_attributes.attributes
    ) == (
        QName(XML_NAMESPACE, "base"),
        QName(XML_NAMESPACE, "lang"),
        QName(XML_NAMESPACE, "space"),
        QName(XML_NAMESPACE, "id"),
    )

    assert tuple(
        attribute.ref
        for attribute in simple_attributes.attributes
    ) == (
        QName(XLINK_NAMESPACE, "type"),
        QName(XLINK_NAMESPACE, "href"),
        QName(XLINK_NAMESPACE, "role"),
        QName(XLINK_NAMESPACE, "arcrole"),
        QName(XLINK_NAMESPACE, "title"),
        QName(XLINK_NAMESPACE, "show"),
        QName(XLINK_NAMESPACE, "actuate"),
    )
    assert simple_attributes.attributes[0].fixed_value == "simple"


def test_complex_type_keeps_direct_local_declarations(
    uad_schema_model: SchemaModel,
) -> None:
    """A UAD complex type retains its direct elements and attributes."""

    about_version = uad_schema_model.complex_types[
        QName(MISMO_NAMESPACE, "ABOUT_VERSION")
    ]

    assert about_version.content is not None
    assert tuple(
        element.name
        for element in about_version.content.elements
    ) == (
        QName(MISMO_NAMESPACE, "AboutVersionIdentifier"),
        QName(MISMO_NAMESPACE, "EXTENSION"),
    )
    assert tuple(
        attribute.name
        for attribute in about_version.attributes
    ) == (
        QName(None, "SequenceNumber"),
    )
    assert about_version.attributes[0].type_name == QName(
        MISMO_NAMESPACE,
        "MISMOSequenceNumber_Base",
    )


def test_named_type_relationships_remain_available(
    uad_schema_model: SchemaModel,
) -> None:
    """Existing named simple- and complex-type relationships remain intact."""

    arcrole_base = uad_schema_model.simple_types[
        QName(XLINK_NAMESPACE, "ArcroleBase")
    ]

    assert arcrole_base.base_type == QName(
        XML_SCHEMA_NAMESPACE,
        "anyURI",
    )
    assert QName(MISMO_NAMESPACE, "MESSAGE") in (
        uad_schema_model.complex_types
    )
