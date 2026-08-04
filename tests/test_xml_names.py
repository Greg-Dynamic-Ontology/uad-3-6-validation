"""Tests for namespace-qualified XML-name utilities."""

import pytest

from app.utilities.xml_names import split_expanded_name


def test_split_expanded_name_returns_namespace_and_local_name() -> None:
    expanded_name = "{https://example.com/uad#}APPRAISAL"

    assert split_expanded_name(expanded_name) == (
        "https://example.com/uad#",
        "APPRAISAL",
    )


def test_split_expanded_name_rejects_unqualified_name() -> None:
    with pytest.raises(
        ValueError,
        match="The XML name must use a namespace",
    ):
        split_expanded_name("APPRAISAL")


def test_split_expanded_name_rejects_missing_closing_brace() -> None:
    with pytest.raises(ValueError):
        split_expanded_name("{https://example.com/uad#APPRAISAL")
