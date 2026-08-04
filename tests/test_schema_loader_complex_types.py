"""Tests for named complex types in the XML Schema loader."""

from pathlib import Path

from app.models.schema_model import ModelGroupKind, QName
from app.services.schema_loader.schema_loader import SchemaLoader


XML_SCHEMA_NAMESPACE = "http://www.w3.org/2001/XMLSchema"
TARGET_NAMESPACE = "https://example.com/schema/customer"
COMPLEX_TYPE_NAME = "CustomerType"


def test_schema_loader_loads_named_complex_type(
    tmp_path: Path,
) -> None:
    """The Logical Schema Model contains a named complex type."""

    schema_path = tmp_path / "customer.xsd"

    schema_path.write_text(
        f"""<?xml version="1.0" encoding="UTF-8"?>
<xs:schema
    xmlns:xs="{XML_SCHEMA_NAMESPACE}"
    xmlns:cus="{TARGET_NAMESPACE}"
    targetNamespace="{TARGET_NAMESPACE}"
    elementFormDefault="qualified">

    <xs:complexType name="{COMPLEX_TYPE_NAME}"/>

</xs:schema>
""",
        encoding="utf-8",
    )

    schema_model = SchemaLoader().load(schema_path)

    expected_name = QName(
        namespace=TARGET_NAMESPACE,
        local_name=COMPLEX_TYPE_NAME,
    )

    assert len(schema_model.complex_types) == 1
    assert expected_name in schema_model.complex_types
    assert schema_model.complex_types[expected_name].name == expected_name


def test_schema_loader_loads_named_complex_type_base_type(
    tmp_path: Path,
) -> None:
    """The Logical Schema Model preserves a complex-type base type."""

    schema_path = tmp_path / "customer.xsd"

    schema_path.write_text(
        f"""<?xml version="1.0" encoding="UTF-8"?>
<xs:schema
    xmlns:xs="{XML_SCHEMA_NAMESPACE}"
    xmlns:cus="{TARGET_NAMESPACE}"
    targetNamespace="{TARGET_NAMESPACE}"
    elementFormDefault="qualified">

    <xs:complexType name="{COMPLEX_TYPE_NAME}">
        <xs:complexContent>
            <xs:extension base="cus:PartyType"/>
        </xs:complexContent>
    </xs:complexType>

</xs:schema>
""",
        encoding="utf-8",
    )

    schema_model = SchemaLoader().load(schema_path)

    expected_name = QName(
        namespace=TARGET_NAMESPACE,
        local_name=COMPLEX_TYPE_NAME,
    )

    assert (
        schema_model.complex_types[expected_name].base_type
        == QName(
            namespace=TARGET_NAMESPACE,
            local_name="PartyType",
        )
    )


def test_schema_loader_loads_named_complex_type_sequence(
    tmp_path: Path,
) -> None:
    """The Logical Schema Model preserves an empty sequence."""

    schema_path = tmp_path / "customer.xsd"

    schema_path.write_text(
        f"""<?xml version="1.0" encoding="UTF-8"?>
<xs:schema
    xmlns:xs="{XML_SCHEMA_NAMESPACE}"
    xmlns:cus="{TARGET_NAMESPACE}"
    targetNamespace="{TARGET_NAMESPACE}"
    elementFormDefault="qualified">

    <xs:complexType name="{COMPLEX_TYPE_NAME}">
        <xs:sequence/>
    </xs:complexType>

</xs:schema>
""",
        encoding="utf-8",
    )

    schema_model = SchemaLoader().load(schema_path)

    expected_name = QName(
        namespace=TARGET_NAMESPACE,
        local_name=COMPLEX_TYPE_NAME,
    )

    content = schema_model.complex_types[expected_name].content

    assert content is not None
    assert content.kind is ModelGroupKind.SEQUENCE
    assert content.elements == ()
    assert content.groups == ()
    assert content.min_occurs == 1
    assert content.max_occurs == 1


def test_schema_loader_loads_sequence_element(
    tmp_path: Path,
) -> None:
    """The Logical Schema Model preserves an element in a sequence."""

    schema_path = tmp_path / "customer.xsd"

    schema_path.write_text(
        f"""<?xml version="1.0" encoding="UTF-8"?>
<xs:schema
    xmlns:xs="{XML_SCHEMA_NAMESPACE}"
    xmlns:cus="{TARGET_NAMESPACE}"
    targetNamespace="{TARGET_NAMESPACE}"
    elementFormDefault="qualified">

    <xs:complexType name="{COMPLEX_TYPE_NAME}">
        <xs:sequence>
            <xs:element
                name="FirstName"
                type="xs:string"/>
        </xs:sequence>
    </xs:complexType>

</xs:schema>
""",
        encoding="utf-8",
    )

    schema_model = SchemaLoader().load(schema_path)

    expected_name = QName(
        namespace=TARGET_NAMESPACE,
        local_name=COMPLEX_TYPE_NAME,
    )

    content = schema_model.complex_types[expected_name].content

    assert content is not None
    assert len(content.elements) == 1

    element = content.elements[0]

    assert element.name == QName(
        namespace=TARGET_NAMESPACE,
        local_name="FirstName",
    )

    assert element.type_name == QName(
        namespace=XML_SCHEMA_NAMESPACE,
        local_name="string",
    )


def test_schema_loader_loads_sequence_element_min_occurs(
    tmp_path: Path,
) -> None:
    """The Logical Schema Model preserves minOccurs."""

    schema_path = tmp_path / "customer.xsd"

    schema_path.write_text(
        f"""<?xml version="1.0" encoding="UTF-8"?>
<xs:schema
    xmlns:xs="{XML_SCHEMA_NAMESPACE}"
    xmlns:cus="{TARGET_NAMESPACE}"
    targetNamespace="{TARGET_NAMESPACE}"
    elementFormDefault="qualified">

    <xs:complexType name="{COMPLEX_TYPE_NAME}">
        <xs:sequence>
            <xs:element
                name="FirstName"
                type="xs:string"
                minOccurs="0"/>
        </xs:sequence>
    </xs:complexType>

</xs:schema>
""",
        encoding="utf-8",
    )

    schema_model = SchemaLoader().load(schema_path)

    expected_name = QName(
        namespace=TARGET_NAMESPACE,
        local_name=COMPLEX_TYPE_NAME,
    )

    content = schema_model.complex_types[expected_name].content

    assert content is not None
    assert len(content.elements) == 1

    element = content.elements[0]

    assert element.min_occurs == 0