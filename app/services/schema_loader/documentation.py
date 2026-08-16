"""Extract human-readable documentation from XML Schema components."""

from __future__ import annotations

import xml.etree.ElementTree as ET

from app.services.schema_loader_context import SchemaLoaderContext


def extract_documentation(
    element: ET.Element,
    context: SchemaLoaderContext,
) -> str | None:
    """Return normalized documentation directly owned by a component.

    Text nested inside XHTML or other markup is retained. Multiple direct
    ``xs:documentation`` blocks are preserved in document order and separated
    by a blank line.
    """

    annotation_tag = _xsd_tag(context, "annotation")
    documentation_tag = _xsd_tag(context, "documentation")
    annotation = element.find(annotation_tag)

    if annotation is None:
        return None

    documentation_blocks: list[str] = []

    for documentation in annotation.findall(documentation_tag):
        normalized_text = _normalize_text(documentation)

        if normalized_text:
            documentation_blocks.append(normalized_text)

    if not documentation_blocks:
        return None

    return "\n\n".join(documentation_blocks)


def _normalize_text(element: ET.Element) -> str:
    """Flatten descendant text and normalize XML formatting whitespace."""

    unnormalized_text = " ".join(element.itertext())
    return " ".join(unnormalized_text.split())


def _xsd_tag(
    context: SchemaLoaderContext,
    local_name: str,
) -> str:
    """Create an expanded XSD tag using the validated schema root."""

    root_tag = context.root.tag
    namespace = root_tag[1:root_tag.index("}")]
    return f"{{{namespace}}}{local_name}"
