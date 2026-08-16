"""Discover and inventory XML Schema documents in a schema closure."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Iterable, Mapping
import xml.etree.ElementTree as ET


XML_SCHEMA_NAMESPACE = "http://www.w3.org/2001/XMLSchema"
SCHEMA_ROOT_TAG = f"{{{XML_SCHEMA_NAMESPACE}}}schema"
XML_SCHEMA_TAG_PREFIX = f"{{{XML_SCHEMA_NAMESPACE}}}"


@dataclass(frozen=True, slots=True)
class SchemaDocument:
    """One parsed XML Schema document in a discovered closure."""

    path: Path
    tree: ET.ElementTree
    root: ET.Element
    namespace_bindings: Mapping[str, str]


@dataclass(frozen=True, slots=True)
class SchemaComponentOccurrence:
    """One XSD component occurrence and its source document."""

    component_kind: str
    source_document: Path


@dataclass(frozen=True, slots=True)
class SchemaComponentInventory:
    """All XSD component occurrences found in a schema closure."""

    occurrences: tuple[SchemaComponentOccurrence, ...]
    counts_by_kind: Mapping[str, int]


def discover_schema_closure(entry_point: Path) -> tuple[SchemaDocument, ...]:
    """Discover an entry-point schema and its recursive local imports.

    Documents are returned in deterministic depth-first order. A resolved
    filesystem path is visited at most once, even when multiple schemas import
    the same document.
    """

    documents: list[SchemaDocument] = []
    visited_paths: set[Path] = set()

    def visit(path: Path) -> None:
        resolved_path = path.resolve()

        if resolved_path in visited_paths:
            return

        visited_paths.add(resolved_path)

        namespace_bindings = _read_namespace_bindings(resolved_path)
        tree = ET.parse(resolved_path)
        root = tree.getroot()

        _validate_schema_root(resolved_path, root)

        documents.append(
            SchemaDocument(
                path=resolved_path,
                tree=tree,
                root=root,
                namespace_bindings=namespace_bindings,
            )
        )

        import_tag = f"{{{XML_SCHEMA_NAMESPACE}}}import"

        for import_element in root.findall(import_tag):
            schema_location = import_element.get("schemaLocation")

            if not schema_location:
                continue

            imported_path = resolved_path.parent / schema_location

            if not imported_path.is_file():
                raise FileNotFoundError(
                    "Imported XML Schema document was not found: "
                    f"{imported_path}"
                )

            visit(imported_path)

    visit(entry_point)

    return tuple(documents)


def inventory_schema_components(
    documents: Iterable[SchemaDocument],
) -> SchemaComponentInventory:
    """Inventory XSD component elements below each schema root.

    The ``xs:schema`` root is validated and retained as document metadata. It
    is the document envelope rather than one of the component kinds in the
    inventory.
    """

    occurrences: list[SchemaComponentOccurrence] = []

    for document in documents:
        _validate_schema_root(document.path, document.root)

        for element in document.root.iter():
            if element is document.root:
                continue

            if not isinstance(element.tag, str):
                continue

            if not element.tag.startswith(XML_SCHEMA_TAG_PREFIX):
                continue

            component_kind = element.tag[len(XML_SCHEMA_TAG_PREFIX):]

            occurrences.append(
                SchemaComponentOccurrence(
                    component_kind=component_kind,
                    source_document=document.path,
                )
            )

    immutable_occurrences = tuple(occurrences)
    counts = Counter(
        occurrence.component_kind
        for occurrence in immutable_occurrences
    )

    return SchemaComponentInventory(
        occurrences=immutable_occurrences,
        counts_by_kind=MappingProxyType(
            dict(sorted(counts.items()))
        ),
    )


def _validate_schema_root(path: Path, root: ET.Element) -> None:
    """Require the XML Schema document root before further processing."""

    if root.tag == SCHEMA_ROOT_TAG:
        return

    raise ValueError(
        "Expected XML Schema document root "
        f"{SCHEMA_ROOT_TAG!r} in {path}; found {root.tag!r}."
    )


def _read_namespace_bindings(path: Path) -> dict[str, str]:
    """Read namespace-prefix bindings declared in an XML document."""

    namespace_bindings: dict[str, str] = {}

    for event, namespace_data in ET.iterparse(
        path,
        events=("start-ns",),
    ):
        if event != "start-ns":
            continue

        if not isinstance(namespace_data, tuple):
            continue

        prefix, namespace_iri = namespace_data

        if not isinstance(prefix, str):
            continue

        if not isinstance(namespace_iri, str):
            continue

        namespace_bindings[prefix] = namespace_iri

    return namespace_bindings
