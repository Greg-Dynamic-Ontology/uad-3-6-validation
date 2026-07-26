"""Load XML Schema documents into the internal SchemaModel."""

from __future__ import annotations

from pathlib import Path
import xml.etree.ElementTree as ET

from app.core.namespaces import SCHEMA_MODEL_NAMESPACE_IRI
from app.models.schema_model import QName, SchemaModel
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

        return schema

    @staticmethod
    def _read_namespace_bindings(path: Path) -> dict[str, str]:
        """Read namespace prefix bindings declared in an XML document."""

        namespace_bindings: dict[str, str] = {}

        for _event, namespace in ET.iterparse(
            path,
            events=("start-ns",),
        ):
            prefix, namespace_iri = namespace
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
    def _load_namespaces(
        context: SchemaLoaderContext,
    ) -> None:
        """Load namespace information into the SchemaModel."""

        del context