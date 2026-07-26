"""Tests for QName resolution within the XML Schema loader."""

from pathlib import Path
import xml.etree.ElementTree as ET

import pytest

from app.core.namespaces import SCHEMA_MODEL_NAMESPACE_IRI
from app.models.schema_model import QName, SchemaModel
from app.services.schema_loader import SchemaLoader
from app.services.schema_loader_context import SchemaLoaderContext


def make_context(
    *,
    target_namespace: str | None = "http://www.mismo.org/residential/2009/schemas",
    namespace_bindings: dict[str, str] | None = None,
) -> SchemaLoaderContext:
    """Create a minimal SchemaLoaderContext for QName resolution tests."""

    if namespace_bindings is None:
        namespace_bindings = {
            "xsd": "http://www.w3.org/2001/XMLSchema",
            "xs": "http://www.w3.org/2001/XMLSchema",
        }

    root = ET.Element("schema")
    tree = ET.ElementTree(root)

    schema = SchemaModel(
        target_namespace=target_namespace,
        namespace_bindings=namespace_bindings,
    )

    return SchemaLoaderContext(
        path=Path("dummy.xsd"),
        tree=tree,
        root=root,
        schema=schema,
    )


def test_resolves_prefixed_qname() -> None:
    """Known prefixes resolve successfully."""

    ctx = make_context()

    qname = SchemaLoader._resolve_qname("xsd:string", ctx)

    assert qname == QName(
        namespace=SCHEMA_MODEL_NAMESPACE_IRI,
        local_name="string",
    )


def test_resolves_unprefixed_qname() -> None:
    """Unprefixed names resolve successfully."""

    ctx = make_context()

    qname = SchemaLoader._resolve_qname(
        "PropertyConditionType",
        ctx,
    )

    assert qname == QName(
        namespace=SCHEMA_MODEL_NAMESPACE_IRI,
        local_name="PropertyConditionType",
    )


def test_unknown_prefix_raises_value_error() -> None:
    """Unknown prefixes are rejected."""

    ctx = make_context()

    with pytest.raises(ValueError, match="Unknown namespace prefix"):
        SchemaLoader._resolve_qname(
            "foo:Bar",
            ctx,
        )


@pytest.mark.parametrize(
    "lexical_qname",
    [
        "",
        ":abc",
        "abc:",
        "a:b:c",
    ],
)
def test_invalid_qname_raises_value_error(
    lexical_qname: str,
) -> None:
    """Malformed lexical QNames are rejected."""

    ctx = make_context()

    with pytest.raises(ValueError):
        SchemaLoader._resolve_qname(
            lexical_qname,
            ctx,
        )