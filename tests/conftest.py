"""Shared pytest command-line options and collection policy."""

from __future__ import annotations

import pytest


CANONICAL_ARTIFACT_MARKER = "canonical_artifact"


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register the explicit comprehensive-artifact test switch."""

    parser.addoption(
        "--run-canonical-artifact",
        action="store_true",
        default=False,
        help="run comprehensive canonical Logical Schema artifact tests",
    )


def pytest_configure(config: pytest.Config) -> None:
    """Document the marker so pytest never reports an unknown marker."""

    config.addinivalue_line(
        "markers",
        "canonical_artifact: comprehensive canonical artifact verification",
    )


def pytest_collection_modifyitems(
    config: pytest.Config,
    items: list[pytest.Item],
) -> None:
    """Deselect comprehensive artifact tests unless explicitly requested."""

    if config.getoption("--run-canonical-artifact"):
        return

    selected: list[pytest.Item] = []
    deselected: list[pytest.Item] = []

    for item in items:
        if CANONICAL_ARTIFACT_MARKER in item.keywords:
            deselected.append(item)
        else:
            selected.append(item)

    if deselected:
        config.hook.pytest_deselected(items=deselected)
        items[:] = selected
