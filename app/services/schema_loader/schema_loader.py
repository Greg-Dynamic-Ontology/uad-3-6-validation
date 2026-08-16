"""Load XML Schema documents into the internal SchemaModel."""

from __future__ import annotations

from pathlib import Path

from app.core.namespaces import SCHEMA_MODEL_NAMESPACE_IRI
from app.models.schema_model import (
    ComponentProcessingDisposition,
    ComplexTypeDefinition,
    QName,
    SchemaModel,
)
from app.services.schema_loader.declarations import (
    load_attribute_group_definitions,
    load_direct_attribute_declarations,
    load_direct_attribute_group_references,
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
    inventory_schema_components,
)
from app.services.schema_loader.type_derivations import (
    inspect_complex_type_derivation,
    load_named_simple_type_definitions,
)
from app.services.schema_loader_context import SchemaLoaderContext
from app.services.schema_loader.wildcard_policy import (
    apply_wildcard_policy,
)


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
        inventory = inventory_schema_components(documents)
        processing_dispositions = apply_wildcard_policy(inventory)

        return self._merge_document_models(
            document_models,
            processing_dispositions=processing_dispositions,
        )

    def _load_document(self, document: SchemaDocument) -> SchemaModel:
        """Load one previously discovered XML Schema document."""

        schema = SchemaModel(
            target_namespace=document.root.attrib.get("targetNamespace"),
            namespace_bindings=dict(document.namespace_bindings),
            schema_imports=document.schema_imports,
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

        object.__setattr__(
            schema,
            "simple_types",
            load_named_simple_type_definitions(
                context,
                self._resolve_schema_qname,
            ),
        )
        self._load_complex_types(context)

        return schema

    @staticmethod
    def _merge_document_models(
        document_models: tuple[SchemaModel, ...],
        *,
        processing_dispositions: tuple[
            ComponentProcessingDisposition,
            ...,
        ] = (),
    ) -> SchemaModel:
        """Merge schema-document models into the entry-point model."""

        if not document_models:
            raise ValueError("A schema closure must contain an entry point.")

        entry_model = document_models[0]
        namespace_bindings = dict(entry_model.namespace_bindings)
        namespaces: set[str] = set()
        schema_imports = []
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
            schema_imports.extend(document_model.schema_imports)

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
            schema_imports=tuple(schema_imports),
            processing_dispositions=processing_dispositions,
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
        for element in context.root.findall(complex_type_tag):
            name = element.get("name")
            if not name:
                continue

            qname = QName(
                namespace=context.schema.target_namespace,
                local_name=name,
            )

            derivation = inspect_complex_type_derivation(
                element,
                context,
                SchemaLoader._resolve_schema_qname,
            )
            content = load_complex_type_content(
                element,
                context,
                SchemaLoader._resolve_schema_qname,
            )

            content_owner = (
                derivation.content_owner
                if derivation.content_owner is not None
                else element
            )
            attributes = load_direct_attribute_declarations(
                content_owner,
                context,
                SchemaLoader._resolve_schema_qname,
            )
            attribute_group_refs = (
                load_direct_attribute_group_references(
                    content_owner,
                    context,
                    SchemaLoader._resolve_schema_qname,
                )
            )

            complex_types[qname] = ComplexTypeDefinition(
                name=qname,
                base_type=derivation.base_type,
                derivation_kind=derivation.kind,
                simple_content=derivation.simple_content,
                content=content,
                attributes=attributes,
                attribute_group_refs=attribute_group_refs,
                documentation=extract_documentation(element, context),
            )

        object.__setattr__(
            context.schema,
            "complex_types",
            complex_types,
        )
