"""Tests for named simple types in the XML Schema loader."""

from pathlib import Path

from app.models.schema_model import Facet, QName
from app.services.schema_loader.schema_loader import SchemaLoader


XML_SCHEMA_NAMESPACE = "http://www.w3.org/2001/XMLSchema"
TARGET_NAMESPACE = "https://example.com/schema/customer"
SIMPLE_TYPE_NAME = "CustomerStatusCode"


def test_schema_loader_loads_named_simple_type(
    tmp_path: Path,
) -> None:
    """The Logical Schema Model contains a named simple type."""

    schema_path = tmp_path / "customer.xsd"

    schema_path.write_text(
        f"""<?xml version="1.0" encoding="UTF-8"?>
<xs:schema
    xmlns:xs="{XML_SCHEMA_NAMESPACE}"
    xmlns:cus="{TARGET_NAMESPACE}"
    targetNamespace="{TARGET_NAMESPACE}"
    elementFormDefault="qualified">

    <xs:simpleType name="{SIMPLE_TYPE_NAME}">
        <xs:restriction base="xs:string"/>
    </xs:simpleType>

</xs:schema>
""",
        encoding="utf-8",
    )

    schema_model = SchemaLoader().load(schema_path)

    expected_name = QName(
        namespace=TARGET_NAMESPACE,
        local_name=SIMPLE_TYPE_NAME,
    )

    assert len(schema_model.simple_types) == 1
    assert expected_name in schema_model.simple_types
    assert schema_model.simple_types[expected_name].name == expected_name


def test_schema_loader_loads_named_simple_type_base_type(
    tmp_path: Path,
) -> None:
    """The Logical Schema Model records a simple type restriction base."""

    schema_path = tmp_path / "customer.xsd"

    schema_path.write_text(
        f"""<?xml version="1.0" encoding="UTF-8"?>
<xs:schema
    xmlns:xs="{XML_SCHEMA_NAMESPACE}"
    xmlns:cus="{TARGET_NAMESPACE}"
    targetNamespace="{TARGET_NAMESPACE}"
    elementFormDefault="qualified">

    <xs:simpleType name="{SIMPLE_TYPE_NAME}">
        <xs:restriction base="xs:string"/>
    </xs:simpleType>

</xs:schema>
""",
        encoding="utf-8",
    )

    schema_model = SchemaLoader().load(schema_path)

    expected_name = QName(
        namespace=TARGET_NAMESPACE,
        local_name=SIMPLE_TYPE_NAME,
    )

    expected_base_type = QName(
        namespace=XML_SCHEMA_NAMESPACE,
        local_name="string",
    )

    assert (
        schema_model.simple_types[expected_name].base_type
        == expected_base_type
    )


def test_schema_loader_loads_named_simple_type_enumeration_values(
    tmp_path: Path,
) -> None:
    """The Logical Schema Model records enumeration values."""

    schema_path = tmp_path / "customer.xsd"

    schema_path.write_text(
        f"""<?xml version="1.0" encoding="UTF-8"?>
<xs:schema
    xmlns:xs="{XML_SCHEMA_NAMESPACE}"
    xmlns:cus="{TARGET_NAMESPACE}"
    targetNamespace="{TARGET_NAMESPACE}"
    elementFormDefault="qualified">

    <xs:simpleType name="{SIMPLE_TYPE_NAME}">
        <xs:restriction base="xs:string">
            <xs:enumeration value="Active"/>
            <xs:enumeration value="Inactive"/>
        </xs:restriction>
    </xs:simpleType>

</xs:schema>
""",
        encoding="utf-8",
    )

    schema_model = SchemaLoader().load(schema_path)

    expected_name = QName(
        namespace=TARGET_NAMESPACE,
        local_name=SIMPLE_TYPE_NAME,
    )

    assert (
        schema_model.simple_types[expected_name].enumeration_values
        == (
            "Active",
            "Inactive",
        )
    )


def test_schema_loader_loads_named_simple_type_restriction_facet(
    tmp_path: Path,
) -> None:
    """The Logical Schema Model records a restriction facet."""

    schema_path = tmp_path / "customer.xsd"

    schema_path.write_text(
        f"""<?xml version="1.0" encoding="UTF-8"?>
<xs:schema
    xmlns:xs="{XML_SCHEMA_NAMESPACE}"
    xmlns:cus="{TARGET_NAMESPACE}"
    targetNamespace="{TARGET_NAMESPACE}"
    elementFormDefault="qualified">

    <xs:simpleType name="{SIMPLE_TYPE_NAME}">
        <xs:restriction base="xs:string">
            <xs:maxLength value="12"/>
        </xs:restriction>
    </xs:simpleType>

</xs:schema>
""",
        encoding="utf-8",
    )

    schema_model = SchemaLoader().load(schema_path)

    expected_name = QName(
        namespace=TARGET_NAMESPACE,
        local_name=SIMPLE_TYPE_NAME,
    )

    assert schema_model.simple_types[expected_name].facets == (
        Facet(
            name="maxLength",
            value="12",
        ),
    )


def test_schema_loader_loads_named_simple_type_union_member_types(
    tmp_path: Path,
) -> None:
    """The Logical Schema Model records union member types."""

    schema_path = tmp_path / "customer.xsd"

    schema_path.write_text(
        f"""<?xml version="1.0" encoding="UTF-8"?>
<xs:schema
    xmlns:xs="{XML_SCHEMA_NAMESPACE}"
    xmlns:cus="{TARGET_NAMESPACE}"
    targetNamespace="{TARGET_NAMESPACE}"
    elementFormDefault="qualified">

    <xs:simpleType name="{SIMPLE_TYPE_NAME}">
        <xs:union memberTypes="xs:string xs:integer"/>
    </xs:simpleType>

</xs:schema>
""",
        encoding="utf-8",
    )

    schema_model = SchemaLoader().load(schema_path)

    expected_name = QName(
        namespace=TARGET_NAMESPACE,
        local_name=SIMPLE_TYPE_NAME,
    )

    assert (
        schema_model.simple_types[expected_name].union_member_types
        == (
            QName(
                namespace=XML_SCHEMA_NAMESPACE,
                local_name="string",
            ),
            QName(
                namespace=XML_SCHEMA_NAMESPACE,
                local_name="integer",
            ),
        )
    )