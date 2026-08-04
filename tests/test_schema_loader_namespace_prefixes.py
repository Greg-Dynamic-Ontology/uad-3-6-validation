"""Tests for namespace handling in the XML Schema loader."""

from pathlib import Path

from app.services.schema_loader.schema_loader import SchemaLoader


XML_SCHEMA_NAMESPACE = "http://www.w3.org/2001/XMLSchema"
CUSTOMER_NAMESPACE = "https://example.com/schema/customer"
COMMON_NAMESPACE = "https://example.com/schema/common"


def test_schema_loader_preserves_namespace_prefixes(
    tmp_path: Path,
) -> None:
    """The Logical Schema Model preserves namespace information."""

    schema_path = tmp_path / "customer.xsd"

    schema_path.write_text(
        f"""<?xml version="1.0" encoding="UTF-8"?>
<xs:schema
    xmlns:xs="{XML_SCHEMA_NAMESPACE}"
    xmlns:cus="{CUSTOMER_NAMESPACE}"
    xmlns:com="{COMMON_NAMESPACE}"
    targetNamespace="{CUSTOMER_NAMESPACE}"
    elementFormDefault="qualified">
</xs:schema>
""",
        encoding="utf-8",
    )

    schema_model = SchemaLoader().load(schema_path)

    assert schema_model.namespace_bindings["xs"] == XML_SCHEMA_NAMESPACE
    assert schema_model.namespace_bindings["cus"] == CUSTOMER_NAMESPACE
    assert schema_model.namespace_bindings["com"] == COMMON_NAMESPACE

    assert XML_SCHEMA_NAMESPACE in schema_model.namespaces
    assert CUSTOMER_NAMESPACE in schema_model.namespaces
    assert COMMON_NAMESPACE in schema_model.namespaces