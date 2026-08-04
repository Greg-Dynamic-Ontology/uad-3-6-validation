"""Tests for target namespace handling in the XML Schema loader."""

from pathlib import Path

from app.services.schema_loader.schema_loader import SchemaLoader


TARGET_NAMESPACE = "https://example.com/schema/customer"


def test_schema_loader_preserves_target_namespace(
    tmp_path: Path,
) -> None:
    """The Logical Schema Model records the XSD target namespace."""

    schema_path = tmp_path / "customer.xsd"

    schema_path.write_text(
        f"""<?xml version="1.0" encoding="UTF-8"?>
<xs:schema
    xmlns:xs="http://www.w3.org/2001/XMLSchema"
    targetNamespace="{TARGET_NAMESPACE}"
    elementFormDefault="qualified">
</xs:schema>
""",
        encoding="utf-8",
    )

    schema_model = SchemaLoader().load(schema_path)

    assert schema_model.target_namespace == TARGET_NAMESPACE