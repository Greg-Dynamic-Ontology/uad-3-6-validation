"""Discover and inventory XML Schema documents in a schema closure."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Iterable, Mapping
import xml.etree.ElementTree as ET

from app.models.schema_model import SchemaImport


XML_SCHEMA_NAMESPACE = "http://www.w3.org/2001/XMLSchema"
SCHEMA_ROOT_TAG = f"{{{XML_SCHEMA_NAMESPACE}}}schema"
XML_SCHEMA_TAG_PREFIX = f"{{{XML_SCHEMA_NAMESPACE}}}"


@dataclass(frozen=True, slots=True)
class SchemaDocument:
    """One parsed XML Schema document in a discovered closure."""

    path: Path
    tree: ET.ElementTree
    root: ET.Element
    target_namespace: str | None
    namespace_bindings: Mapping[str, str]
    schema_imports: tuple[SchemaImport, ...]
    schema_includes: tuple[Path, ...]


@dataclass(frozen=True, slots=True)
class SchemaComponentOccurrence:
    """One XSD component occurrence and its source document."""

    component_kind: str
    source_document: Path
    source_index: int


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
    visited_namespaces: dict[Path, str | None] = {}

    def visit(
        path: Path,
        inherited_target_namespace: str | None = None,
    ) -> None:
        resolved_path = path.resolve()

        if resolved_path in visited_namespaces:
            previous_namespace = visited_namespaces[resolved_path]
            if (
                inherited_target_namespace is not None
                and previous_namespace != inherited_target_namespace
            ):
                raise ValueError(
                    "Included XML Schema document was reached with "
                    "incompatible target namespaces: "
                    f"{resolved_path} ({previous_namespace!r} and "
                    f"{inherited_target_namespace!r})."
                )
            return

        namespace_bindings = _read_namespace_bindings(resolved_path)
        tree = ET.parse(resolved_path)
        root = tree.getroot()

        _validate_schema_root(resolved_path, root)
        target_namespace = (
            root.attrib.get("targetNamespace")
            or inherited_target_namespace
        )
        visited_namespaces[resolved_path] = target_namespace
        schema_imports = _read_schema_imports(resolved_path, root)
        schema_includes = _read_schema_includes(resolved_path, root)

        documents.append(
            SchemaDocument(
                path=resolved_path,
                tree=tree,
                root=root,
                target_namespace=target_namespace,
                namespace_bindings=namespace_bindings,
                schema_imports=schema_imports,
                schema_includes=schema_includes,
            )
        )

        for schema_import in schema_imports:
            imported_path = schema_import.resolved_document

            if imported_path is None:
                continue

            if not imported_path.is_file():
                raise FileNotFoundError(
                    "Imported XML Schema document was not found: "
                    f"{imported_path}"
                )

            visit(imported_path)

        for included_path in schema_includes:
            if not included_path.is_file():
                raise FileNotFoundError(
                    "Included XML Schema document was not found: "
                    f"{included_path}"
                )

            visit(
                included_path,
                inherited_target_namespace=target_namespace,
            )

    visit(entry_point)

    return tuple(documents)


def _read_schema_imports(
    source_document: Path,
    root: ET.Element,
) -> tuple[SchemaImport, ...]:
    """Read every import occurrence from one schema document."""

    import_tag = f"{{{XML_SCHEMA_NAMESPACE}}}import"
    schema_imports: list[SchemaImport] = []

    for element in root.findall(import_tag):
        schema_location = element.get("schemaLocation")
        resolved_document = (
            (source_document.parent / schema_location).resolve()
            if schema_location
            else None
        )

        schema_imports.append(
            SchemaImport(
                namespace=element.get("namespace"),
                schema_location=schema_location,
                source_document=source_document,
                resolved_document=resolved_document,
            )
        )

    return tuple(schema_imports)


def _read_schema_includes(
    source_document: Path,
    root: ET.Element,
) -> tuple[Path, ...]:
    """Resolve every local include occurrence in one schema document."""

    include_tag = f"{{{XML_SCHEMA_NAMESPACE}}}include"
    included_paths: list[Path] = []

    for element in root.findall(include_tag):
        schema_location = element.get("schemaLocation")
        if not schema_location:
            raise ValueError(
                "XML Schema include requires schemaLocation in "
                f"{source_document}."
            )

        included_paths.append(
            (source_document.parent / schema_location).resolve()
        )

    return tuple(included_paths)


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
        source_index = 0

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
                    source_index=source_index,
                )
            )
            source_index += 1

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
