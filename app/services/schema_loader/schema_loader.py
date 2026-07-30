"""Load XML Schema documents into the internal SchemaModel."""

from __future__ import annotations

from pathlib import Path
import xml.etree.ElementTree as ET

from app.core.namespaces import SCHEMA_MODEL_NAMESPACE_IRI
from app.models.schema_model import (
    ComplexTypeDefinition,
    ElementDeclaration,
    Facet,
    ModelGroup,
    ModelGroupKind,
    QName,
    SchemaModel,
    SimpleTypeDefinition,
)
from app.services.schema_loader_context import SchemaLoaderContext


class SchemaLoader:
    """Load an XML Schema document into a SchemaModel."""

    def load(self, path: Path) -> SchemaModel:
        """Load an XML Schema document."""

        namespace_bindings = self._read_namespace_bindings(path)
        tree = ET.parse(path)
        root = tree.getroot()

        schema = SchemaModel(
            target_namespace=root.attrib.get("targetNamespace"),
            namespace_bindings=namespace_bindings,
        )

        context = SchemaLoaderContext(
            path=path,
            tree=tree,
            root=root,
            schema=schema,
        )

        self._load_namespaces(context)
        self._load_simple_types(context)
        self._load_complex_types(context)

        return schema

    @staticmethod
    def _read_namespace_bindings(path: Path) -> dict[str, str]:
        """Read namespace prefix bindings declared in an XML document."""

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

    @staticmethod
    def _resolve_qname(
        lexical_qname: str,
        context: SchemaLoaderContext,
    ) -> QName:
        """Resolve an XML lexical QName to a SchemaModel QName."""

        lexical_qname = lexical_qname.strip()

        if not lexical_qname:
            raise ValueError("QName must not be empty.")

        if lexical_qname.count(":") > 1:
            raise ValueError(
                f"Malformed QName: {lexical_qname!r}."
            )

        if ":" in lexical_qname:
            prefix, local_name = lexical_qname.split(":", maxsplit=1)

            if not prefix or not local_name:
                raise ValueError(
                    f"Malformed QName: {lexical_qname!r}."
                )

            if prefix not in context.schema.namespace_bindings:
                raise ValueError(
                    f"Unknown namespace prefix: {prefix!r}."
                )
        else:
            local_name = lexical_qname

        return QName(
            namespace=SCHEMA_MODEL_NAMESPACE_IRI,
            local_name=local_name,
        )

    @staticmethod
    def _resolve_schema_qname(
        lexical_qname: str,
        context: SchemaLoaderContext,
    ) -> QName:
        """Resolve an XML Schema lexical QName to its namespace URI."""

        lexical_qname = lexical_qname.strip()

        if not lexical_qname:
            raise ValueError("QName must not be empty.")

        if lexical_qname.count(":") > 1:
            raise ValueError(
                f"Malformed QName: {lexical_qname!r}."
            )

        if ":" in lexical_qname:
            prefix, local_name = lexical_qname.split(":", maxsplit=1)

            if not prefix or not local_name:
                raise ValueError(
                    f"Malformed QName: {lexical_qname!r}."
                )

            try:
                namespace = context.schema.namespace_bindings[prefix]
            except KeyError as error:
                raise ValueError(
                    f"Unknown namespace prefix: {prefix!r}."
                ) from error
        else:
            local_name = lexical_qname
            namespace = context.schema.target_namespace

        return QName(
            namespace=namespace,
            local_name=local_name,
        )

    @staticmethod
    def _load_namespaces(
        context: SchemaLoaderContext,
    ) -> None:
        """Load namespace information into the SchemaModel."""

        object.__setattr__(
            context.schema,
            "namespaces",
            frozenset(context.schema.namespace_bindings.values()),
        )

    @staticmethod
    def _load_simple_types(
        context: SchemaLoaderContext,
    ) -> None:
        """Load named simple types into the SchemaModel."""

        simple_types: dict[QName, SimpleTypeDefinition] = {}

        root_tag = context.root.tag
        if not root_tag.startswith("{"):
            return

        xml_schema_namespace = root_tag[1:root_tag.index("}")]
        simple_type_tag = f"{{{xml_schema_namespace}}}simpleType"
        restriction_tag = f"{{{xml_schema_namespace}}}restriction"
        union_tag = f"{{{xml_schema_namespace}}}union"

        for element in context.root.findall(simple_type_tag):
            name = element.get("name")
            if not name:
                continue

            qname = QName(
                namespace=context.schema.target_namespace,
                local_name=name,
            )

            base_type = None
            enumeration_values: list[str] = []
            facets: list[Facet] = []
            union_member_types: list[QName] = []

            restriction = element.find(restriction_tag)

            if restriction is not None:
                lexical_base_type = restriction.get("base")

                if lexical_base_type:
                    base_type = SchemaLoader._resolve_schema_qname(
                        lexical_base_type,
                        context,
                    )

                for child in restriction:
                    local_name = child.tag.split("}", 1)[1]

                    if local_name == "enumeration":
                        value = child.get("value")
                        if value is not None:
                            enumeration_values.append(value)

                    elif local_name == "maxLength":
                        value = child.get("value")
                        if value is not None:
                            facets.append(
                                Facet(
                                    name="maxLength",
                                    value=value,
                                )
                            )

            union = element.find(union_tag)

            if union is not None:
                lexical_member_types = union.get("memberTypes")

                if lexical_member_types:
                    for lexical_member_type in lexical_member_types.split():
                        union_member_types.append(
                            SchemaLoader._resolve_schema_qname(
                                lexical_member_type,
                                context,
                            )
                        )

            simple_types[qname] = SimpleTypeDefinition(
                name=qname,
                base_type=base_type,
                facets=tuple(facets),
                enumeration_values=tuple(enumeration_values),
                union_member_types=tuple(union_member_types),
            )

        object.__setattr__(
            context.schema,
            "simple_types",
            simple_types,
        )

    @staticmethod
    def _load_complex_types(
        context: SchemaLoaderContext,
    ) -> None:
        """Load named complex types into the SchemaModel."""

        complex_types: dict[QName, ComplexTypeDefinition] = {}

        root_tag = context.root.tag
        if not root_tag.startswith("{"):
            return

        xml_schema_namespace = root_tag[1:root_tag.index("}")]
        complex_type_tag = f"{{{xml_schema_namespace}}}complexType"
        complex_content_tag = (
            f"{{{xml_schema_namespace}}}complexContent"
        )
        extension_tag = f"{{{xml_schema_namespace}}}extension"
        sequence_tag = f"{{{xml_schema_namespace}}}sequence"
        element_tag = f"{{{xml_schema_namespace}}}element"

        for element in context.root.findall(complex_type_tag):
            name = element.get("name")
            if not name:
                continue

            qname = QName(
                namespace=context.schema.target_namespace,
                local_name=name,
            )

            base_type = None
            content = None

            complex_content = element.find(complex_content_tag)
            if complex_content is not None:
                extension = complex_content.find(extension_tag)
                if extension is not None:
                    lexical_base = extension.get("base")
                    if lexical_base:
                        base_type = (
                            SchemaLoader._resolve_schema_qname(
                                lexical_base,
                                context,
                            )
                        )

            sequence = element.find(sequence_tag)
            if sequence is not None:
                element_declarations: list[ElementDeclaration] = []

                for child_element in sequence.findall(element_tag):
                    child_name = child_element.get("name")
                    if not child_name:
                        continue

                    lexical_type_name = child_element.get("type")
                    type_name = None

                    if lexical_type_name:
                        type_name = (
                            SchemaLoader._resolve_schema_qname(
                                lexical_type_name,
                                context,
                            )
                        )

                    lexical_min_occurs = child_element.get(
                        "minOccurs",
                        "1",
                    )
                    min_occurs = int(lexical_min_occurs)

                    lexical_max_occurs = child_element.get(
                        "maxOccurs"
                    )

                    if lexical_max_occurs is None:
                        max_occurs = max(1, min_occurs)
                    elif lexical_max_occurs == "unbounded":
                        max_occurs = None
                    else:
                        max_occurs = int(lexical_max_occurs)

                    element_declarations.append(
                        ElementDeclaration(
                            name=QName(
                                namespace=context.schema.target_namespace,
                                local_name=child_name,
                            ),
                            type_name=type_name,
                            min_occurs=min_occurs,
                            max_occurs=max_occurs,
                        )
                    )

                content = ModelGroup(
                    kind=ModelGroupKind.SEQUENCE,
                    elements=tuple(element_declarations),
                )

            complex_types[qname] = ComplexTypeDefinition(
                name=qname,
                base_type=base_type,
                content=content,
            )

        object.__setattr__(
            context.schema,
            "complex_types",
            complex_types,
        )