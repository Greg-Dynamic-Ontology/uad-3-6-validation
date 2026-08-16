"""Load XML Schema model groups into the Logical Schema Model."""

from __future__ import annotations

from collections.abc import Callable

from app.models.schema_model import (
    ModelGroup,
    ModelGroupKind,
    ModelGroupReference,
    QName,
)
from app.services.schema_loader.declarations import (
    load_element_declaration,
)
from app.services.schema_loader_context import SchemaLoaderContext


SchemaQNameResolver = Callable[
    [str, SchemaLoaderContext],
    QName,
]


def load_model_group_definitions(
    context: SchemaLoaderContext,
    resolve_schema_qname: SchemaQNameResolver,
) -> dict[QName, ModelGroup]:
    """Load global named model-group definitions by expanded QName."""

    definitions: dict[QName, ModelGroup] = {}
    group_tag = _xsd_tag(context, "group")

    for element in context.root.findall(group_tag):
        name = element.get("name")
        if not name:
            continue

        compositor = _find_content_particle(element, context)
        if compositor is None:
            continue

        content = _load_content_particle(
            compositor,
            context,
            resolve_schema_qname,
        )
        if not isinstance(content, ModelGroup):
            continue

        definitions[
            QName(context.schema.target_namespace, name)
        ] = content

    return definitions


def load_complex_type_content(
    complex_type: object,
    context: SchemaLoaderContext,
    resolve_schema_qname: SchemaQNameResolver,
) -> ModelGroup | ModelGroupReference | None:
    """Load the content particle directly owned by a complex type."""

    owner = complex_type
    complex_content = complex_type.find(
        _xsd_tag(context, "complexContent")
    )

    if complex_content is not None:
        owner = complex_content.find(_xsd_tag(context, "extension"))

        if owner is None:
            owner = complex_content.find(
                _xsd_tag(context, "restriction")
            )

        if owner is None:
            return None

    particle = _find_content_particle(owner, context)
    if particle is None:
        return None

    return _load_content_particle(
        particle,
        context,
        resolve_schema_qname,
    )


def _load_content_particle(
    element: object,
    context: SchemaLoaderContext,
    resolve_schema_qname: SchemaQNameResolver,
) -> ModelGroup | ModelGroupReference:
    """Recursively load a sequence, choice, or group reference."""

    local_name = _local_name(element.tag)

    if local_name == "group":
        reference = element.get("ref")
        if not reference:
            raise ValueError("A model-group use must provide a ref QName.")

        return ModelGroupReference(
            ref=resolve_schema_qname(reference, context),
            min_occurs=_read_min_occurs(element),
            max_occurs=_read_max_occurs(element),
        )

    kind = {
        "sequence": ModelGroupKind.SEQUENCE,
        "choice": ModelGroupKind.CHOICE,
    }.get(local_name)

    if kind is None:
        raise ValueError(
            f"Unsupported model-group compositor: {local_name!r}."
        )

    particles: list[object] = []

    for child in element:
        child_local_name = _local_name(child.tag)

        if child_local_name == "element":
            declaration = load_element_declaration(
                child,
                context,
                resolve_schema_qname,
                global_declaration=False,
            )
            if declaration is not None:
                particles.append(declaration)
        elif child_local_name in {"sequence", "choice", "group"}:
            particles.append(
                _load_content_particle(
                    child,
                    context,
                    resolve_schema_qname,
                )
            )

    return ModelGroup(
        kind=kind,
        particles=tuple(particles),
        min_occurs=_read_min_occurs(element),
        max_occurs=_read_max_occurs(element),
    )


def _find_content_particle(
    parent: object,
    context: SchemaLoaderContext,
) -> object | None:
    """Return the first directly owned model-group particle."""

    supported_tags = {
        _xsd_tag(context, "sequence"),
        _xsd_tag(context, "choice"),
        _xsd_tag(context, "group"),
    }

    return next(
        (child for child in parent if child.tag in supported_tags),
        None,
    )


def _read_min_occurs(element: object) -> int:
    """Read a particle's minimum occurrence constraint."""

    return int(element.get("minOccurs", "1"))


def _read_max_occurs(element: object) -> int | None:
    """Read a particle's maximum occurrence constraint."""

    lexical_value = element.get("maxOccurs", "1")
    return None if lexical_value == "unbounded" else int(lexical_value)


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
