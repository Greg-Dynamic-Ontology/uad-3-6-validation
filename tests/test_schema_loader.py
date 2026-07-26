from pathlib import Path

from app.models.schema_model import SchemaModel
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

MISMO_TARGET_NAMESPACE = (
    "http://www.mismo.org/residential/2009/schemas"
)

XML_SCHEMA_NAMESPACE = "http://www.w3.org/2001/XMLSchema"


def test_loader_returns_schema_model() -> None:
    assert COMBINED_SCHEMA_PATH.exists()

    loader = SchemaLoader()

    schema = loader.load(COMBINED_SCHEMA_PATH)

    assert isinstance(schema, SchemaModel)


def test_loader_reads_target_namespace() -> None:
    loader = SchemaLoader()

    schema = loader.load(COMBINED_SCHEMA_PATH)

    assert schema.target_namespace == MISMO_TARGET_NAMESPACE


def test_loader_reads_namespace_bindings() -> None:
    loader = SchemaLoader()

    schema = loader.load(COMBINED_SCHEMA_PATH)

    declared_namespaces = set(schema.namespace_bindings.values())

    assert XML_SCHEMA_NAMESPACE in declared_namespaces
    assert MISMO_TARGET_NAMESPACE in declared_namespaces