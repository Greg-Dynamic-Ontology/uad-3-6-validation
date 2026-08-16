"""Load XML Schema documents into the internal SchemaModel."""

from __future__ import annotations

from pathlib import Path

from app.core.namespaces import SCHEMA_MODEL_NAMESPACE_IRI
from app.models.schema_model import (
    ComplexTypeDefinition,
    Facet,
    QName,
    SchemaModel,
    SimpleTypeDefinition,
)
from app.services.schema_loader.declarations import (
    load_attribute_group_definitions,
    load_direct_attribute_declarations,
    load_global_attribute_declarations,
    load_global_element_declarations,
)
from app.services.schema_loader.documentation import extract_documentation
from app.services.schema_loader.model_groups import (
    load_complex_type_content,
    load_model_group_definitions,
)
from app.services.schema_loader.schema_closure import (
    SchemaDocument,
    discover_schema_closure,
)
from app.services.schema_loader_context import SchemaLoaderContext


XML_NAMESPACE = "http://www.w3.org/XML/1998/namespace"


class SchemaLoader:
    """Load an XML Schema document and its imports into a SchemaModel."""

    def load(self, path: Path) -> SchemaModel:
        """Load an XML Schema document and its recursive local imports."""

        documents = discover_schema_closure(path)
        document_models = tuple(
            self._load_document(document)
            for document in documents
        )

        return self._merge_document_models(document_models)

    def _load_document(self, document: SchemaDocument) -> SchemaModel:
        """Load one previously discovered XML Schema document."""

        schema = SchemaModel(
            target_namespace=document.root.attrib.get("targetNamespace"),
            namespace_bindings=dict(document.namespace_bindings),
        )

        context = SchemaLoaderContext(
            path=document.path,
            tree=document.tree,
            root=document.root,
            schema=schema,
        )

        self._load_namespaces(context)

        object.__setattr__(
            schema,
            "elements",
            load_global_element_declarations(
                context,
                self._resolve_schema_qname,
            ),
        )
        object.__setattr__(
            schema,
            "attributes",
            load_global_attribute_declarations(
                context,
                self._resolve_schema_qname,
            ),
        )
        object.__setattr__(
            schema,
            "attribute_groups",
            load_attribute_group_definitions(
                context,
                self._resolve_schema_qname,
            ),
        )
        object.__setattr__(
            schema,
            "model_groups",
            load_model_group_definitions(
                context,
                self._resolve_schema_qname,
            ),
        )

        self._load_simple_types(context)
        self._load_complex_types(context)

        return schema

    @staticmethod
    def _merge_document_models(
        document_models: tuple[SchemaModel, ...],
    ) -> SchemaModel:
        """Merge schema-document models into the entry-point model."""

        if not document_models:
            raise ValueError("A schema closure must contain an entry point.")

        entry_model = document_models[0]
        namespace_bindings = dict(entry_model.namespace_bindings)
        namespaces: set[str] = set()
        elements = {}
        complex_types = {}
        simple_types = {}
        attributes = {}
        attribute_groups = {}
        model_groups = {}

        for document_model in document_models:
            for prefix, namespace_iri in (
                document_model.namespace_bindings.items()
            ):
                namespace_bindings.setdefault(prefix, namespace_iri)

            namespaces.update(document_model.namespaces)

            if document_model.target_namespace:
                namespaces.add(document_model.target_namespace)

            elements.update(document_model.elements)
            complex_types.update(document_model.complex_types)
            simple_types.update(document_model.simple_types)
            attributes.update(document_model.attributes)
            attribute_groups.update(document_model.attribute_groups)
            model_groups.update(document_model.model_groups)

        return SchemaModel(
            target_namespace=entry_model.target_namespace,
            namespace_bindings=namespace_bindings,
            elements=elements,
            complex_types=complex_types,
            simple_types=simple_types,
            attributes=attributes,
            attribute_groups=attribute_groups,
            model_groups=model_groups,
            namespaces=frozenset(namespaces),
        )

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

            if prefix == "xml":
                namespace = XML_NAMESPACE
            else:
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
                documentation=extract_documentation(element, context),
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

        for element in context.root.findall(complex_type_tag):
            name = element.get("name")
            if not name:
                continue

            qname = QName(
                namespace=context.schema.target_namespace,
                local_name=name,
            )

            base_type = None
            content = load_complex_type_content(
                element,
                context,
                SchemaLoader._resolve_schema_qname,
            )

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

            attributes = load_direct_attribute_declarations(
                element,
                context,
                SchemaLoader._resolve_schema_qname,
            )

            complex_types[qname] = ComplexTypeDefinition(
                name=qname,
                base_type=base_type,
                content=content,
                attributes=attributes,
                documentation=extract_documentation(element, context),
            )

        object.__setattr__(
            context.schema,
            "complex_types",
            complex_types,
        )
