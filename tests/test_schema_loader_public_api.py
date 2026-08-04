"""Characterization tests for the SchemaLoader public API."""

from pathlib import Path

from app.models.schema_model import SchemaModel
from app.services.schema_loader.schema_loader import SchemaLoader


XML_SCHEMA_NAMESPACE = "http://www.w3.org/2001/XMLSchema"
TARGET_NAMESPACE = "https://example.com/schema/public-api"


def test_schema_loader_remains_available_from_public_import_path() -> None:
    """SchemaLoader remains available from app.services.schema_loader."""

    loader = SchemaLoader()

    assert isinstance(loader, SchemaLoader)


def test_schema_loader_load_accepts_a_schema_path_and_returns_schema_model(
    tmp_path: Path,
) -> None:
    """The public load(path) operation returns a SchemaModel."""

    schema_path = tmp_path / "public-api.xsd"

    schema_path.write_text(
        f"""<?xml version="1.0" encoding="UTF-8"?>
<xs:schema
    xmlns:xs="{XML_SCHEMA_NAMESPACE}"
    xmlns:pub="{TARGET_NAMESPACE}"
    targetNamespace="{TARGET_NAMESPACE}"
    elementFormDefault="qualified">
</xs:schema>
""",
        encoding="utf-8",
    )

    schema_model = SchemaLoader().load(schema_path)

    assert isinstance(schema_model, SchemaModel)
    assert schema_model.target_namespace == TARGET_NAMESPACE
