"""Acceptance tests for preserving UAD XML Schema documentation."""

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


@pytest.fixture(scope="module")
def uad_schema_model() -> SchemaModel:
    """Load the official Combined UAD schema closure once for this suite."""

    assert COMBINED_SCHEMA_PATH.exists()
    return SchemaLoader().load(COMBINED_SCHEMA_PATH)


def test_global_declaration_documentation_is_preserved(
    uad_schema_model: SchemaModel,
) -> None:
    """IT-5R2S2: Global declarations retain their documentation."""

    message = uad_schema_model.elements[
        QName(MISMO_NAMESPACE, "MESSAGE")
    ]
    attribute_extension = uad_schema_model.attribute_groups[
        QName(MISMO_NAMESPACE, "AttributeExtension")
    ]

    assert message.documentation is not None
    assert "MESSAGE is the root node for V3" in message.documentation

    assert attribute_extension.documentation is not None
    assert (
        "ability to extend an instance document"
        in attribute_extension.documentation
    )


def test_named_type_documentation_is_preserved(
    uad_schema_model: SchemaModel,
) -> None:
    """Named complex and simple types retain their documentation."""

    about_version = uad_schema_model.complex_types[
        QName(MISMO_NAMESPACE, "ABOUT_VERSION")
    ]
    arcrole_base = uad_schema_model.simple_types[
        QName(XLINK_NAMESPACE, "ArcroleBase")
    ]

    assert about_version.documentation is not None
    assert (
        "identifies the version of the specification"
        in about_version.documentation
    )

    assert arcrole_base.documentation is not None
    assert "base set of arcroles" in arcrole_base.documentation


def test_local_declaration_documentation_is_preserved(
    uad_schema_model: SchemaModel,
) -> None:
    """Local element and attribute declarations retain documentation."""

    about_version = uad_schema_model.complex_types[
        QName(MISMO_NAMESPACE, "ABOUT_VERSION")
    ]

    assert about_version.content is not None

    identifier = about_version.content.elements[0]
    sequence_number = about_version.attributes[0]

    assert identifier.documentation is not None
    assert (
        "user defined version identifier"
        in identifier.documentation
    )

    assert sequence_number.documentation is not None
    assert (
        "provide an order to multi-instance sibling elements"
        in sequence_number.documentation
    )


def test_mixed_xhtml_documentation_is_normalized(
    uad_schema_model: SchemaModel,
) -> None:
    """Text nested in XHTML markup remains readable downstream."""

    xml_base = uad_schema_model.attributes[
        QName(XML_NAMESPACE, "base")
    ]

    assert xml_base.documentation is not None
    assert "base (as an attribute name)" in xml_base.documentation
    assert (
        "provides a URI to be used as the base"
        in xml_base.documentation
    )
    assert "http://www.w3.org/TR/xmlbase/" in xml_base.documentation
    assert "\n" not in xml_base.documentation
