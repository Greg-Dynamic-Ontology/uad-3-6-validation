"""Shared pytest command-line options, collection policy, and test clocks."""

from __future__ import annotations

from datetime import date

import pytest


CANONICAL_ARTIFACT_MARKER = "canonical_artifact"


@pytest.fixture
def required_data_baseline_clock(monkeypatch: pytest.MonkeyPatch) -> date:
    """Evaluate the historical SF1 baseline as of 2019-09-20.

    Tests must explicitly request this fixture. It preserves the historical
    XML and makes its age-dependent expectations repeatable.

    Production validation continues to use today's date. Chronology boundary
    tests retain their own separately recorded evaluation dates.
    """
    from app.services import date_chronology_required_data

    class BaselineDate(date):
        @classmethod
        def today(cls):
            return cls(2019, 9, 20)

    monkeypatch.setattr(
        date_chronology_required_data,
        "date",
        BaselineDate,
    )
    return BaselineDate.today()


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