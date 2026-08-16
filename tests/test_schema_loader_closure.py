"""Tests for discovery and inventory of the UAD XML Schema closure."""

from collections import Counter
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest

from app.models.schema_model import QName
from app.services.schema_loader import SchemaLoader
import app.services.schema_loader.schema_closure as schema_closure


PROJECT_ROOT = Path(__file__).resolve().parents[1]
COMBINED_SCHEMA_DIRECTORY = (
    PROJECT_ROOT
    / "specs"
    / "UAD"
    / "GSE_UAD_3.6.0_v1.3"
    / "Combined"
)
ENTRY_POINT_SCHEMA = (
    COMBINED_SCHEMA_DIRECTORY / "GSE_UAD_3.6.0_v1.3.xsd"
)
XLINK_SCHEMA = (
    COMBINED_SCHEMA_DIRECTORY / "GSE_UAD_3.6.0_xlink_v1.3.xsd"
)
XML_SCHEMA = COMBINED_SCHEMA_DIRECTORY / "xml.xsd"

XLINK_NAMESPACE = "http://www.w3.org/1999/xlink"
XML_SCHEMA_NAMESPACE = "http://www.w3.org/2001/XMLSchema"
SCHEMA_ROOT_TAG = f"{{{XML_SCHEMA_NAMESPACE}}}schema"

EXPECTED_COUNTS_BY_KIND = {
    "annotation": 5260,
    "any": 368,
    "anyAttribute": 1,
    "attribute": 993,
    "attributeGroup": 1144,
    "choice": 4,
    "complexType": 1297,
    "documentation": 5269,
    "element": 2221,
    "enumeration": 1313,
    "extension": 202,
    "fractionDigits": 1,
    "group": 12,
    "import": 3,
    "maxInclusive": 1,
    "maxLength": 5,
    "minInclusive": 3,
    "minLength": 2,
    "pattern": 5,
    "restriction": 222,
    "sequence": 1093,
    "simpleContent": 202,
    "simpleType": 224,
    "union": 2,
}


def test_loader_follows_imports_and_visits_each_schema_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """IT-5R1S1: Follow imports through the UAD schema closure."""

    expected_schema_paths = {
        path.resolve()
        for path in (
            ENTRY_POINT_SCHEMA,
            XLINK_SCHEMA,
            XML_SCHEMA,
        )
    }
    assert all(path.exists() for path in expected_schema_paths)

    parsed_paths: list[Path] = []
    original_parse = ET.parse

    def recording_parse(
        source: str | Path,
        *args: object,
        **kwargs: object,
    ) -> ET.ElementTree:
        parsed_paths.append(Path(source).resolve())
        return original_parse(source, *args, **kwargs)

    monkeypatch.setattr(ET, "parse", recording_parse)

    schema = SchemaLoader().load(ENTRY_POINT_SCHEMA)

    visits = Counter(
        path for path in parsed_paths if path in expected_schema_paths
    )

    assert set(visits) == expected_schema_paths
    assert all(count == 1 for count in visits.values())
    assert QName(XLINK_NAMESPACE, "ArcroleBase") in schema.simple_types


def test_discovery_requires_an_xml_schema_document_root(
    tmp_path: Path,
) -> None:
    """An XML Schema root is the permission gate for further processing."""

    invalid_path = tmp_path / "not-an-xml-schema.xml"
    invalid_path.write_text(
        "<document><element /></document>",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="XML Schema document root",
    ) as error:
        schema_closure.discover_schema_closure(invalid_path)

    assert str(invalid_path.resolve()) in str(error.value)


def test_inventory_records_every_uad_xsd_component_occurrence() -> None:
    """IT-5R1S2: Inventory every XSD component occurrence."""

    documents = schema_closure.discover_schema_closure(
        ENTRY_POINT_SCHEMA
    )

    assert all(
        document.root.tag == SCHEMA_ROOT_TAG
        for document in documents
    )

    inventory_function = getattr(
        schema_closure,
        "inventory_schema_components",
        None,
    )
    assert callable(inventory_function), (
        "schema_closure must provide inventory_schema_components()"
    )

    inventory = inventory_function(documents)

    occurrence_counts = Counter(
        occurrence.component_kind
        for occurrence in inventory.occurrences
    )
    source_counts = Counter(
        occurrence.source_document.resolve()
        for occurrence in inventory.occurrences
    )

    assert occurrence_counts == EXPECTED_COUNTS_BY_KIND
    assert dict(inventory.counts_by_kind) == EXPECTED_COUNTS_BY_KIND
    assert len(inventory.occurrences) == sum(
        EXPECTED_COUNTS_BY_KIND.values()
    )
    assert source_counts == {
        ENTRY_POINT_SCHEMA.resolve(): 19598,
        XLINK_SCHEMA.resolve(): 215,
        XML_SCHEMA.resolve(): 34,
    }
