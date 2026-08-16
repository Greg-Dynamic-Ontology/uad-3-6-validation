"""Load XML Schema type derivations into the Logical Schema Model."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from app.models.schema_model import (
    Facet,
    QName,
    SimpleTypeDefinition,
    TypeDerivationKind,
)
from app.services.schema_loader.documentation import extract_documentation
from app.services.schema_loader_context import SchemaLoaderContext


SchemaQNameResolver = Callable[
    [str, SchemaLoaderContext],
    QName,
]


@dataclass(frozen=True, slots=True)
class ComplexTypeDerivation:
    """Resolved derivation metadata and the element owning added content."""

    kind: TypeDerivationKind | None = None
    base_type: QName | None = None
    simple_content: bool = False
    content_owner: object | None = None


def load_named_simple_type_definitions(
    context: SchemaLoaderContext,
    resolve_schema_qname: SchemaQNameResolver,
) -> dict[QName, SimpleTypeDefinition]:
    """Load global named simple-type definitions by expanded QName."""

    definitions: dict[QName, SimpleTypeDefinition] = {}
    simple_type_tag = _xsd_tag(context, "simpleType")

    for element in context.root.findall(simple_type_tag):
        local_name = element.get("name")
        if not local_name:
            continue

        name = QName(context.schema.target_namespace, local_name)
        definitions[name] = load_simple_type_definition(
            element,
            context,
            resolve_schema_qname,
            name=name,
        )

    return definitions


def load_inline_simple_type(
    parent: object,
    context: SchemaLoaderContext,
    resolve_schema_qname: SchemaQNameResolver,
) -> SimpleTypeDefinition | None:
    """Load a simple type declared directly inside another component."""

    element = parent.find(_xsd_tag(context, "simpleType"))
    if element is None:
        return None

    return load_simple_type_definition(
        element,
        context,
        resolve_schema_qname,
        name=None,
    )


def load_simple_type_definition(
    element: object,
    context: SchemaLoaderContext,
    resolve_schema_qname: SchemaQNameResolver,
    *,
    name: QName | None,
) -> SimpleTypeDefinition:
    """Load one named or anonymous simple-type definition recursively."""

    restriction = element.find(_xsd_tag(context, "restriction"))
    if restriction is not None:
        return _load_restriction(
            element,
            restriction,
            context,
            resolve_schema_qname,
            name=name,
        )

    union = element.find(_xsd_tag(context, "union"))
    if union is not None:
        return _load_union(
            element,
            union,
            context,
            resolve_schema_qname,
            name=name,
        )

    return SimpleTypeDefinition(
        name=name,
        documentation=extract_documentation(element, context),
    )


def inspect_complex_type_derivation(
    complex_type: object,
    context: SchemaLoaderContext,
    resolve_schema_qname: SchemaQNameResolver,
) -> ComplexTypeDerivation:
    """Identify a complex type's extension or restriction owner."""

    for content_name, simple_content in (
        ("simpleContent", True),
        ("complexContent", False),
    ):
        content = complex_type.find(_xsd_tag(context, content_name))
        if content is None:
            continue

        for derivation_name, kind in (
            ("extension", TypeDerivationKind.EXTENSION),
            ("restriction", TypeDerivationKind.RESTRICTION),
        ):
            derivation = content.find(
                _xsd_tag(context, derivation_name)
            )
            if derivation is None:
                continue

            lexical_base = derivation.get("base")
            base_type = (
                resolve_schema_qname(lexical_base, context)
                if lexical_base
                else None
            )

            return ComplexTypeDerivation(
                kind=kind,
                base_type=base_type,
                simple_content=simple_content,
                content_owner=derivation,
            )

    return ComplexTypeDerivation(content_owner=complex_type)


def _load_restriction(
    simple_type: object,
    restriction: object,
    context: SchemaLoaderContext,
    resolve_schema_qname: SchemaQNameResolver,
    *,
    name: QName | None,
) -> SimpleTypeDefinition:
    """Load a simple-type restriction and currently supported constraints."""

    lexical_base = restriction.get("base")
    base_type = (
        resolve_schema_qname(lexical_base, context)
        if lexical_base
        else None
    )
    enumeration_values: list[str] = []
    facets: list[Facet] = []

    for child in restriction:
        local_name = _local_name(child.tag)
        value = child.get("value")

        if value is None:
            continue

        if local_name == "enumeration":
            enumeration_values.append(value)
        elif local_name == "maxLength":
            facets.append(Facet(name=local_name, value=value))

    return SimpleTypeDefinition(
        name=name,
        base_type=base_type,
        derivation_kind=TypeDerivationKind.RESTRICTION,
        facets=tuple(facets),
        enumeration_values=tuple(enumeration_values),
        documentation=extract_documentation(simple_type, context),
    )


def _load_union(
    simple_type: object,
    union: object,
    context: SchemaLoaderContext,
    resolve_schema_qname: SchemaQNameResolver,
    *,
    name: QName | None,
) -> SimpleTypeDefinition:
    """Load named and anonymous union members in declaration order."""

    members: list[QName | SimpleTypeDefinition] = []
    lexical_member_types = union.get("memberTypes")

    if lexical_member_types:
        members.extend(
            resolve_schema_qname(lexical_member, context)
            for lexical_member in lexical_member_types.split()
        )

    for child in union.findall(_xsd_tag(context, "simpleType")):
        members.append(
            load_simple_type_definition(
                child,
                context,
                resolve_schema_qname,
                name=None,
            )
        )

    return SimpleTypeDefinition(
        name=name,
        derivation_kind=TypeDerivationKind.UNION,
        union_members=tuple(members),
        documentation=extract_documentation(simple_type, context),
    )


def _xsd_tag(
    context: SchemaLoaderContext,
    local_name: str,
) -> str:
    """Create an expanded XSD tag using the validated schema root."""

    root_tag = context.root.tag
    namespace = root_tag[1:root_tag.index("}")]
    return f"{{{namespace}}}{local_name}"


def _local_name(tag: str) -> str:
    """Return the local name from an expanded XML element name."""

    return tag.rsplit("}", maxsplit=1)[-1]
