"""Load XML Schema declarations into the Logical Schema Model."""

from __future__ import annotations

from collections.abc import Callable

from app.models.schema_model import (
    AttributeDeclaration,
    AttributeGroupDefinition,
    ElementDeclaration,
    QName,
)
from app.services.schema_loader.documentation import extract_documentation
from app.services.schema_loader.type_derivations import (
    load_inline_simple_type,
)
from app.services.schema_loader_context import SchemaLoaderContext


SchemaQNameResolver = Callable[
    [str, SchemaLoaderContext],
    QName,
]


def load_global_element_declarations(
    context: SchemaLoaderContext,
    resolve_schema_qname: SchemaQNameResolver,
) -> dict[QName, ElementDeclaration]:
    """Load global element declarations indexed by expanded QName."""

    element_tag = _xsd_tag(context, "element")
    declarations: dict[QName, ElementDeclaration] = {}

    for element in context.root.findall(element_tag):
        declaration = load_element_declaration(
            element,
            context,
            resolve_schema_qname,
            global_declaration=True,
        )

        if declaration is None or declaration.name is None:
            continue

        declarations[declaration.name] = declaration

    return declarations


def load_global_attribute_declarations(
    context: SchemaLoaderContext,
    resolve_schema_qname: SchemaQNameResolver,
) -> dict[QName, AttributeDeclaration]:
    """Load global attribute declarations indexed by expanded QName."""

    attribute_tag = _xsd_tag(context, "attribute")
    declarations: dict[QName, AttributeDeclaration] = {}

    for element in context.root.findall(attribute_tag):
        declaration = _load_attribute_declaration(
            element,
            context,
            resolve_schema_qname,
            global_declaration=True,
        )

        if declaration is None or declaration.name is None:
            continue

        declarations[declaration.name] = declaration

    return declarations


def load_attribute_group_definitions(
    context: SchemaLoaderContext,
    resolve_schema_qname: SchemaQNameResolver,
) -> dict[QName, AttributeGroupDefinition]:
    """Load global attribute-group definitions and their memberships."""

    attribute_group_tag = _xsd_tag(context, "attributeGroup")
    attribute_tag = _xsd_tag(context, "attribute")
    definitions: dict[QName, AttributeGroupDefinition] = {}

    for element in context.root.findall(attribute_group_tag):
        name = element.get("name")
        if not name:
            continue

        qname = QName(
            namespace=context.schema.target_namespace,
            local_name=name,
        )
        attributes = tuple(
            declaration
            for child in element.findall(attribute_tag)
            if (
                declaration := _load_attribute_declaration(
                    child,
                    context,
                    resolve_schema_qname,
                    global_declaration=False,
                )
            )
            is not None
        )
        referenced_groups = tuple(
            resolve_schema_qname(reference, context)
            for child in element.findall(attribute_group_tag)
            if (reference := child.get("ref"))
        )

        definitions[qname] = AttributeGroupDefinition(
            name=qname,
            attributes=attributes,
            referenced_groups=referenced_groups,
            documentation=extract_documentation(element, context),
        )

    return definitions


def load_direct_attribute_declarations(
    parent: object,
    context: SchemaLoaderContext,
    resolve_schema_qname: SchemaQNameResolver,
) -> tuple[AttributeDeclaration, ...]:
    """Load attribute declarations directly owned by a complex type."""

    attribute_tag = _xsd_tag(context, "attribute")

    return tuple(
        declaration
        for child in parent.findall(attribute_tag)
        if (
            declaration := _load_attribute_declaration(
                child,
                context,
                resolve_schema_qname,
                global_declaration=False,
            )
        )
        is not None
    )


def load_direct_attribute_group_references(
    parent: object,
    context: SchemaLoaderContext,
    resolve_schema_qname: SchemaQNameResolver,
) -> tuple[QName, ...]:
    """Load attribute-group references directly owned by a component."""

    attribute_group_tag = _xsd_tag(context, "attributeGroup")

    return tuple(
        resolve_schema_qname(reference, context)
        for child in parent.findall(attribute_group_tag)
        if (reference := child.get("ref"))
    )


def load_element_declaration(
    element: object,
    context: SchemaLoaderContext,
    resolve_schema_qname: SchemaQNameResolver,
    *,
    global_declaration: bool,
) -> ElementDeclaration | None:
    """Load one named element declaration or element reference."""

    name = element.get("name")
    reference = element.get("ref")

    if not name and not reference:
        return None

    declaration_name = None
    declaration_reference = None

    if name:
        declaration_name = _declared_qname(
            element,
            name,
            context,
            global_declaration=global_declaration,
            attribute=False,
        )
    elif reference:
        declaration_reference = resolve_schema_qname(
            reference,
            context,
        )

    lexical_type = element.get("type")
    type_name = (
        resolve_schema_qname(lexical_type, context)
        if lexical_type
        else None
    )

    return ElementDeclaration(
        name=declaration_name,
        ref=declaration_reference,
        type_name=type_name,
        min_occurs=_read_min_occurs(element),
        max_occurs=_read_max_occurs(element),
        documentation=extract_documentation(element, context),
    )


def _load_attribute_declaration(
    element: object,
    context: SchemaLoaderContext,
    resolve_schema_qname: SchemaQNameResolver,
    *,
    global_declaration: bool,
) -> AttributeDeclaration | None:
    """Load one named attribute declaration or attribute reference."""

    name = element.get("name")
    reference = element.get("ref")

    if not name and not reference:
        return None

    declaration_name = None
    declaration_reference = None

    if name:
        declaration_name = _declared_qname(
            element,
            name,
            context,
            global_declaration=global_declaration,
            attribute=True,
        )
    elif reference:
        declaration_reference = resolve_schema_qname(
            reference,
            context,
        )

    lexical_type = element.get("type")
    type_name = (
        resolve_schema_qname(lexical_type, context)
        if lexical_type
        else None
    )

    return AttributeDeclaration(
        name=declaration_name,
        ref=declaration_reference,
        type_name=type_name,
        required=element.get("use") == "required",
        default_value=element.get("default"),
        fixed_value=element.get("fixed"),
        documentation=extract_documentation(element, context),
        inline_simple_type=load_inline_simple_type(
            element,
            context,
            resolve_schema_qname,
        ),
    )


def _declared_qname(
    element: object,
    local_name: str,
    context: SchemaLoaderContext,
    *,
    global_declaration: bool,
    attribute: bool,
) -> QName:
    """Resolve the expanded name assigned to a declaration."""

    if global_declaration:
        namespace = context.schema.target_namespace
    else:
        explicit_form = element.get("form")
        default_name = (
            "attributeFormDefault"
            if attribute
            else "elementFormDefault"
        )
        default_form = context.root.get(default_name, "unqualified")
        effective_form = explicit_form or default_form
        namespace = (
            context.schema.target_namespace
            if effective_form == "qualified"
            else None
        )

    return QName(
        namespace=namespace,
        local_name=local_name,
    )


def _read_min_occurs(element: object) -> int:
    """Read an element-use minimum occurrence constraint."""

    return int(element.get("minOccurs", "1"))


def _read_max_occurs(element: object) -> int | None:
    """Read an element-use maximum occurrence constraint."""

    lexical_value = element.get("maxOccurs")

    if lexical_value is None:
        return max(1, _read_min_occurs(element))

    if lexical_value == "unbounded":
        return None

    return int(lexical_value)


def _xsd_tag(
    context: SchemaLoaderContext,
    local_name: str,
) -> str:
    """Create an expanded XSD tag using the validated schema root."""

    root_tag = context.root.tag
    namespace = root_tag[1:root_tag.index("}")]
    return f"{{{namespace}}}{local_name}"
