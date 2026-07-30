from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest
from lxml import etree

PROJECT_ROOT = Path(__file__).resolve().parents[1]

COMBINED_SCHEMA = (
    PROJECT_ROOT
    / "specs"
    / "UAD"
    / "GSE_UAD_3.6.0_v1.3"
    / "Combined"
    / "GSE_UAD_3.6.0_v1.3.xsd"
)

INDIVIDUAL_SCHEMA = (
    PROJECT_ROOT
    / "specs"
    / "UAD"
    / "GSE_UAD_3.6.0_v1.3"
    / "Individual"
    / "GSE_UAD_3.6.0_v1.3.xsd"
)

XS_NS = "http://www.w3.org/2001/XMLSchema"
XS = f"{{{XS_NS}}}"


@dataclass(frozen=True)
class LogicalSchemaComponents:
    global_elements: frozenset[str]
    global_attributes: frozenset[str]
    complex_types: frozenset[str]
    simple_types: frozenset[str]


def _qualified_name(target_namespace: str | None, local_name: str) -> str:
    if target_namespace:
        return f"{{{target_namespace}}}{local_name}"

    return local_name


def _included_schema_documents(
    schema_path: Path,
) -> tuple[tuple[Path, str | None], ...]:
    """
    Return the entry schema and every schema reached recursively through
    xs:include, together with each document's effective target namespace.

    Relative schemaLocation values are resolved relative to the schema file
    containing the xs:include declaration.

    An included schema without its own targetNamespace inherits the effective
    target namespace of the including schema. This is XML Schema chameleon
    include behavior.

    Duplicate and circular includes are handled safely.
    """
    discovered: list[tuple[Path, str | None]] = []
    visited: set[Path] = set()

    def visit(
        current_path: Path,
        inherited_target_namespace: str | None = None,
    ) -> None:
        resolved_path = current_path.expanduser().resolve()

        if resolved_path in visited:
            return

        assert resolved_path.is_file(), (
            f"Schema file does not exist: {resolved_path}"
        )

        document = etree.parse(str(resolved_path))
        schema = document.getroot()

        assert schema.tag == f"{XS}schema", (
            f"Expected xs:schema root in {resolved_path}, "
            f"found {schema.tag!r}"
        )

        declared_target_namespace = schema.get("targetNamespace")
        effective_target_namespace = (
            declared_target_namespace or inherited_target_namespace
        )

        visited.add(resolved_path)
        discovered.append(
            (resolved_path, effective_target_namespace)
        )

        for include in schema.findall(f"{XS}include"):
            schema_location = include.get("schemaLocation")

            assert schema_location, (
                f"xs:include without schemaLocation in {resolved_path}"
            )

            include_path = Path(schema_location)

            if not include_path.is_absolute():
                include_path = resolved_path.parent / include_path

            visit(
                include_path,
                effective_target_namespace,
            )

    visit(schema_path)

    return tuple(discovered)


def _logical_schema_components(
    schema_path: Path,
) -> LogicalSchemaComponents:
    """
    Return the global declarations represented by an entry-point XSD and its
    recursive xs:include closure.

    Only declarations whose parent is xs:schema are counted. Local elements
    and attributes nested inside complex types are intentionally excluded.
    """
    global_elements: set[str] = set()
    global_attributes: set[str] = set()
    complex_types: set[str] = set()
    simple_types: set[str] = set()

    for included_path, target_namespace in _included_schema_documents(
        schema_path
    ):
        document = etree.parse(str(included_path))
        schema = document.getroot()

        for declaration in schema:
            name = declaration.get("name")

            if not name:
                continue

            qualified_name = _qualified_name(target_namespace, name)

            if declaration.tag == f"{XS}element":
                global_elements.add(qualified_name)
            elif declaration.tag == f"{XS}attribute":
                global_attributes.add(qualified_name)
            elif declaration.tag == f"{XS}complexType":
                complex_types.add(qualified_name)
            elif declaration.tag == f"{XS}simpleType":
                simple_types.add(qualified_name)

    return LogicalSchemaComponents(
        global_elements=frozenset(global_elements),
        global_attributes=frozenset(global_attributes),
        complex_types=frozenset(complex_types),
        simple_types=frozenset(simple_types),
    )


@pytest.fixture(scope="module")
def combined_schema() -> LogicalSchemaComponents:
    return _logical_schema_components(COMBINED_SCHEMA)


@pytest.fixture(scope="module")
def individual_schema() -> LogicalSchemaComponents:
    return _logical_schema_components(INDIVIDUAL_SCHEMA)


def test_combined_schema_has_global_elements(
    combined_schema: LogicalSchemaComponents,
) -> None:
    assert combined_schema.global_elements


def test_combined_schema_has_no_global_attributes(
    combined_schema: LogicalSchemaComponents,
) -> None:
    """
    UAD 3.6 declares no global xs:attribute definitions.
    """
    assert combined_schema.global_attributes == frozenset()


def test_combined_schema_has_complex_types(
    combined_schema: LogicalSchemaComponents,
) -> None:
    assert combined_schema.complex_types


def test_combined_schema_has_simple_types(
    combined_schema: LogicalSchemaComponents,
) -> None:
    assert combined_schema.simple_types


def test_global_element_counts_match(
    combined_schema: LogicalSchemaComponents,
    individual_schema: LogicalSchemaComponents,
) -> None:
    assert len(combined_schema.global_elements) == len(
        individual_schema.global_elements
    )


def test_global_attribute_counts_match(
    combined_schema: LogicalSchemaComponents,
    individual_schema: LogicalSchemaComponents,
) -> None:
    assert len(combined_schema.global_attributes) == len(
        individual_schema.global_attributes
    )


def test_complex_type_counts_match(
    combined_schema: LogicalSchemaComponents,
    individual_schema: LogicalSchemaComponents,
) -> None:
    assert len(combined_schema.complex_types) == len(
        individual_schema.complex_types
    )


def test_simple_type_counts_match(
    combined_schema: LogicalSchemaComponents,
    individual_schema: LogicalSchemaComponents,
) -> None:
    assert len(combined_schema.simple_types) == len(
        individual_schema.simple_types
    )


def test_combined_and_individual_schema_have_same_global_elements(
    combined_schema: LogicalSchemaComponents,
    individual_schema: LogicalSchemaComponents,
) -> None:
    assert combined_schema.global_elements == individual_schema.global_elements


def test_combined_and_individual_schema_have_same_global_attributes(
    combined_schema: LogicalSchemaComponents,
    individual_schema: LogicalSchemaComponents,
) -> None:
    assert combined_schema.global_attributes == individual_schema.global_attributes


def test_combined_and_individual_schema_have_same_complex_types(
    combined_schema: LogicalSchemaComponents,
    individual_schema: LogicalSchemaComponents,
) -> None:
    assert combined_schema.complex_types == individual_schema.complex_types


def test_combined_and_individual_schema_have_same_simple_types(
    combined_schema: LogicalSchemaComponents,
    individual_schema: LogicalSchemaComponents,
) -> None:
    assert combined_schema.simple_types == individual_schema.simple_types


def test_combined_and_individual_schema_models_are_equal(
    combined_schema: LogicalSchemaComponents,
    individual_schema: LogicalSchemaComponents,
) -> None:
    assert combined_schema == individual_schema
