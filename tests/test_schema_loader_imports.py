"""Acceptance tests for UAD XML Schema import processing."""

from pathlib import Path

import pytest

from app.models.schema_model import QName, SchemaModel
from app.services.schema_loader import SchemaLoader
from app.services.schema_loader.schema_closure import (
    SchemaDocument,
    discover_schema_closure,
)


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
XML_NAMESPACE = "http://www.w3.org/XML/1998/namespace"


@pytest.fixture(scope="module")
def uad_schema_model() -> SchemaModel:
    """Load the official Combined UAD schema closure once for this suite."""

    assert COMBINED_SCHEMA_PATH.exists()
    return SchemaLoader().load(COMBINED_SCHEMA_PATH)


@pytest.fixture(scope="module")
def uad_schema_closure() -> tuple[SchemaDocument, ...]:
    """Discover the official Combined UAD schema closure once."""

    return discover_schema_closure(COMBINED_SCHEMA_PATH)


def test_imports_preserve_namespace_and_schema_location(
    uad_schema_model: SchemaModel,
) -> None:
    """IT-5R5S1: Every import retains its declared packaging metadata."""

    schema_imports = getattr(uad_schema_model, "schema_imports", ())

    assert tuple(
        (schema_import.namespace, schema_import.schema_location)
        for schema_import in schema_imports
    ) == (
        (
            XLINK_NAMESPACE,
            "GSE_UAD_3.6.0_xlink_v1.3.xsd",
        ),
        (XML_NAMESPACE, "xml.xsd"),
        (XML_NAMESPACE, "xml.xsd"),
    )


def test_imports_preserve_source_and_resolved_documents(
    uad_schema_model: SchemaModel,
    uad_schema_closure: tuple[SchemaDocument, ...],
) -> None:
    """Each import connects its source schema to a document in the closure."""

    schema_imports = getattr(uad_schema_model, "schema_imports", ())
    closure_paths = {
        document.path
        for document in uad_schema_closure
    }

    assert tuple(
        (
            schema_import.source_document.name,
            schema_import.resolved_document.name,
        )
        for schema_import in schema_imports
    ) == (
        (
            "GSE_UAD_3.6.0_v1.3.xsd",
            "GSE_UAD_3.6.0_xlink_v1.3.xsd",
        ),
        ("GSE_UAD_3.6.0_v1.3.xsd", "xml.xsd"),
        ("GSE_UAD_3.6.0_xlink_v1.3.xsd", "xml.xsd"),
    )
    assert all(
        schema_import.resolved_document in closure_paths
        for schema_import in schema_imports
    )


def test_imported_schema_declarations_participate_in_loaded_model(
    uad_schema_model: SchemaModel,
) -> None:
    """Declarations from both imported namespaces remain available."""

    assert QName(XLINK_NAMESPACE, "ArcroleBase") in (
        uad_schema_model.simple_types
    )
    assert QName(XML_NAMESPACE, "lang") in uad_schema_model.attributes
