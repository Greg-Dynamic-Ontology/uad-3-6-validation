"""Acceptance tests for governed schema-source IRIs."""

from __future__ import annotations

from hashlib import sha256
from importlib import import_module
from pathlib import Path
from types import ModuleType

import pytest
from rdflib import URIRef


SCHEMA_SOURCE_IRI_PREFIX = (
    "https://dynamicontology.com/uad36/source/sha256/"
)

SCHEMA_ONE = b"""<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:element name="Example" type="xs:string"/>
</xs:schema>
"""

SCHEMA_TWO = b"""<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:element name="Different" type="xs:integer"/>
</xs:schema>
"""


def _schema_source_iri_module() -> ModuleType:
    """Load the public source-identity API after test collection."""

    try:
        return import_module("app.core.schema_source_iri")
    except ModuleNotFoundError as error:
        if error.name != "app.core.schema_source_iri":
            raise
        pytest.fail(
            "Governed schema-source IRI minting is not yet implemented: "
            "expected module app.core.schema_source_iri.",
            pytrace=False,
        )


def _mint_schema_source_iri(source_document: Path) -> URIRef:
    """Call the required public minting function with a clear red failure."""

    module = _schema_source_iri_module()
    mint = getattr(module, "mint_schema_source_iri", None)
    if mint is None:
        pytest.fail(
            "app.core.schema_source_iri must provide "
            "mint_schema_source_iri().",
            pytrace=False,
        )
    return mint(source_document)


def _write_schema(path: Path, content: bytes) -> Path:
    """Create one schema source used by an acceptance test."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def test_schema_source_receives_a_governed_content_addressed_iri(
    tmp_path: Path,
) -> None:
    """IT-8R2S1: Assign a governed IRI to a schema source."""

    source_document = _write_schema(tmp_path / "source.xsd", SCHEMA_ONE)

    source_iri = _mint_schema_source_iri(source_document)

    expected_digest = sha256(SCHEMA_ONE).hexdigest()
    assert isinstance(source_iri, URIRef)
    assert str(source_iri) == SCHEMA_SOURCE_IRI_PREFIX + expected_digest
    assert str(tmp_path) not in str(source_iri)
    assert source_document.name not in str(source_iri)


def test_identical_schema_content_in_different_locations_has_the_same_iri(
    tmp_path: Path,
) -> None:
    """IT-8R2S2: Recognize the same source in different locations."""

    first_source = _write_schema(
        tmp_path / "first-location" / "first-name.xsd",
        SCHEMA_ONE,
    )
    second_source = _write_schema(
        tmp_path / "second-location" / "second-name.xsd",
        SCHEMA_ONE,
    )

    assert _mint_schema_source_iri(first_source) == (
        _mint_schema_source_iri(second_source)
    )


def test_different_schema_content_with_the_same_filename_has_distinct_iris(
    tmp_path: Path,
) -> None:
    """IT-8R2S3: Distinguish different sources with the same file name."""

    first_source = _write_schema(
        tmp_path / "first-location" / "schema.xsd",
        SCHEMA_ONE,
    )
    second_source = _write_schema(
        tmp_path / "second-location" / "schema.xsd",
        SCHEMA_TWO,
    )

    assert _mint_schema_source_iri(first_source) != (
        _mint_schema_source_iri(second_source)
    )
