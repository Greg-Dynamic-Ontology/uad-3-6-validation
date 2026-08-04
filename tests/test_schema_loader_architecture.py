"""Architectural tests for the SchemaLoader implementation."""

import importlib


def test_schema_loader_namespaces_module_exists() -> None:
    """Namespace handling is implemented as its own module."""

    module = importlib.import_module(
        "app.services.schema_loader.namespaces"
    )

    assert module is not None