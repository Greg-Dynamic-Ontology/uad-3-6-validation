"""Project loaded XML instances into RDF graphs."""

from __future__ import annotations

from collections import defaultdict
from hashlib import sha256
from xml.etree import ElementTree
from xml.etree.ElementTree import Element

from rdflib import Graph, Literal, Namespace, RDF, RDFS, URIRef
from rdflib.namespace import OWL, SKOS

from app.models.appraisal import LoadedAppraisal
from app.utilities.xml_names import split_expanded_name


INSTANCE_NAMESPACE = "https://dynamicontology.com/uad36/instance/"
UAD_SCHEMA = Namespace("https://dynamicontology.com/uad36/schema#")


class RdfProjectionStage:
    """Run RDF projection using an appraisal already loaded in memory."""

    def __init__(self, *, projector: object) -> None:
        self.projector = projector

    def run(self, *, loaded_appraisal: LoadedAppraisal) -> Graph:
        return self.projector.project(
            xml_bytes=loaded_appraisal.xml_bytes,
            source_name=loaded_appraisal.source_name,
        )


class RdfProjector:
    """Project XML using a governed ontology or the legacy name mapping."""

    def __init__(self, *, ontology: Graph | None = None) -> None:
        self.ontology = ontology

    def project(self, *, xml_bytes: bytes, source_name: str) -> Graph:
        """Project XML bytes into an RDF instance graph."""

        root = ElementTree.fromstring(xml_bytes)
        root_namespace, root_local_name = split_expanded_name(root.tag)
        graph = Graph()
        root_resource = URIRef(
            f"{INSTANCE_NAMESPACE}{source_name}#{root_local_name}"
        )

        if self.ontology is None:
            root_class = URIRef(f"{root_namespace}{root_local_name}")
        else:
            root_property = self._resolve_property(root.tag)
            root_class = self._property_range(root_property)
            if root_class is None or not self._is_class(root_class):
                self._record_unresolved(
                    graph, source_name, root.tag, root_local_name
                )
                root_class = None

        if root_class is not None:
            graph.add((root_resource, RDF.type, root_class))

        self._project_attributes(
            graph=graph,
            element=root,
            resource=root_resource,
            source_name=source_name,
            parent_path=root_local_name,
        )
        self._project_children(
            graph=graph,
            parent_element=root,
            parent_resource=root_resource,
            parent_path=root_local_name,
            source_name=source_name,
        )
        return graph

    def _project_children(
        self,
        *,
        graph: Graph,
        parent_element: Element,
        parent_resource: URIRef,
        parent_path: str,
        source_name: str,
    ) -> None:
        """Project the children of an XML element."""

        sibling_counts: defaultdict[str, int] = defaultdict(int)
        for child in parent_element:
            child_namespace, child_local_name = split_expanded_name(
                child.tag
            )

            if self.ontology is None:
                predicate = URIRef(
                    f"{child_namespace}{child_local_name}"
                )
            else:
                predicate = self._resolve_property(child.tag)
                if predicate is None:
                    self._record_unresolved(
                        graph,
                        source_name,
                        child.tag,
                        f"{parent_path}/{child_local_name}",
                    )
                    continue

            if len(child) == 0:
                self._project_leaf_element(
                    graph=graph,
                    parent_resource=parent_resource,
                    predicate=predicate,
                    child=child,
                    source_name=source_name,
                    path=f"{parent_path}/{child_local_name}",
                )
                self._project_attributes(
                    graph=graph,
                    element=child,
                    resource=parent_resource,
                    source_name=source_name,
                    parent_path=f"{parent_path}/{child_local_name}",
                )
                continue

            sibling_counts[child_local_name] += 1
            sibling_number = sibling_counts[child_local_name]
            child_path = (
                f"{parent_path}/{child_local_name}-{sibling_number}"
            )
            child_resource = URIRef(
                f"{INSTANCE_NAMESPACE}{source_name}#{child_path}"
            )

            if self.ontology is None:
                child_class = URIRef(
                    f"{child_namespace}{child_local_name}"
                )
            else:
                child_class = self._property_range(predicate)
                if child_class is None or not self._is_class(child_class):
                    self._record_unresolved(
                        graph, source_name, child.tag, child_path
                    )
                    continue

            graph.add((parent_resource, predicate, child_resource))
            graph.add((child_resource, RDF.type, child_class))
            self._project_attributes(
                graph=graph,
                element=child,
                resource=child_resource,
                source_name=source_name,
                parent_path=child_path,
            )
            self._project_children(
                graph=graph,
                parent_element=child,
                parent_resource=child_resource,
                parent_path=child_path,
                source_name=source_name,
            )

    def _project_attributes(
        self,
        *,
        graph: Graph,
        element: Element,
        resource: URIRef,
        source_name: str,
        parent_path: str,
    ) -> None:
        """Project attributes as governed literal or concept properties."""

        element_namespace, _ = split_expanded_name(element.tag)
        for attribute_name, attribute_value in element.attrib.items():
            if self.ontology is None:
                if not attribute_name.startswith("{"):
                    continue
                namespace, local_name = split_expanded_name(attribute_name)
                predicate = URIRef(f"{namespace}{local_name}")
            else:
                if attribute_name.startswith("{"):
                    namespace, local_name = split_expanded_name(
                        attribute_name
                    )
                else:
                    namespace, local_name = None, attribute_name
                lookup_name = attribute_name
                if namespace is None and element_namespace is not None:
                    lookup_name = f"{{{element_namespace}}}{local_name}"
                predicate = self._resolve_property(lookup_name)
                if predicate is None:
                    self._record_unresolved(
                        graph,
                        source_name,
                        lookup_name,
                        f"{parent_path}/@{local_name}",
                    )
                    continue

            value = self._governed_value(
                graph,
                predicate,
                attribute_value,
                source_name,
                attribute_name,
                f"{parent_path}/@{local_name}",
            )
            if value is not None:
                graph.add((resource, predicate, value))

    def _project_leaf_element(
        self,
        *,
        graph: Graph,
        parent_resource: URIRef,
        predicate: URIRef,
        child: Element,
        source_name: str,
        path: str,
    ) -> None:
        """Project one leaf as a typed literal or controlled term."""

        text = child.text
        if text is None or not text.strip():
            return
        lexical_value = text.strip()

        if self.ontology is None:
            value: Literal | URIRef | None = Literal(lexical_value)
        else:
            value = self._governed_value(
                graph,
                predicate,
                lexical_value,
                source_name,
                child.tag,
                path,
            )
        if value is not None:
            graph.add((parent_resource, predicate, value))

    def _resolve_property(self, expanded_name: str) -> URIRef | None:
        """Resolve one XML QName through schema-component metadata."""

        assert self.ontology is not None
        candidates: set[URIRef] = set()
        for component in self.ontology.subjects(
            UAD_SCHEMA.sourceQName, Literal(expanded_name)
        ):
            for term in self.ontology.objects(
                component, UAD_SCHEMA.projectsTo
            ):
                if isinstance(term, URIRef) and self._is_property(term):
                    candidates.add(term)
        if not candidates:
            return None
        return sorted(candidates, key=str)[0]

    def _property_range(self, predicate: URIRef | None) -> URIRef | None:
        """Return the single governed range of a property."""

        if self.ontology is None or predicate is None:
            return None
        ranges = sorted(
            (
                value
                for value in self.ontology.objects(predicate, RDFS.range)
                if isinstance(value, URIRef)
            ),
            key=str,
        )
        return ranges[0] if ranges else None

    def _is_property(self, term: URIRef) -> bool:
        """Return whether the governed ontology declares a property."""

        assert self.ontology is not None
        return any(
            (term, RDF.type, property_type) in self.ontology
            for property_type in (
                RDF.Property,
                OWL.DatatypeProperty,
                OWL.ObjectProperty,
            )
        )

    def _is_class(self, term: URIRef) -> bool:
        """Return whether the governed ontology declares a class."""

        assert self.ontology is not None
        return (
            (term, RDF.type, OWL.Class) in self.ontology
            or (term, RDF.type, RDFS.Class) in self.ontology
        )

    def _governed_value(
        self,
        graph: Graph,
        predicate: URIRef,
        lexical_value: str,
        source_name: str,
        expanded_name: str,
        path: str,
    ) -> Literal | URIRef | None:
        """Create the value required by the property's governed range."""

        if self.ontology is None:
            return Literal(lexical_value)
        range_iri = self._property_range(predicate)
        if range_iri is None:
            self._record_unresolved(
                graph, source_name, expanded_name, path
            )
            return None

        if range_iri == SKOS.Concept:
            schemes = tuple(
                self.ontology.objects(predicate, UAD_SCHEMA.conceptScheme)
            )
            for concept in self.ontology.subjects(
                SKOS.prefLabel, Literal(lexical_value)
            ):
                if (
                    isinstance(concept, URIRef)
                    and (concept, RDF.type, SKOS.Concept) in self.ontology
                    and any(
                        (concept, SKOS.inScheme, scheme) in self.ontology
                        for scheme in schemes
                    )
                ):
                    return concept
            self._record_unresolved(
                graph, source_name, expanded_name, path
            )
            return None

        return Literal(lexical_value, datatype=range_iri)

    @staticmethod
    def _record_unresolved(
        graph: Graph,
        source_name: str,
        expanded_name: str,
        path: str,
    ) -> None:
        """Keep an unmapped XML name visible as a disposition."""

        semantic_key = f"{source_name}|{path}|{expanded_name}"
        digest = sha256(semantic_key.encode("utf-8")).hexdigest()
        disposition = UAD_SCHEMA[f"instance-disposition-{digest}"]
        graph.add(
            (
                disposition,
                RDF.type,
                UAD_SCHEMA.InstanceProjectionDisposition,
            )
        )
        graph.add(
            (
                disposition,
                UAD_SCHEMA.projectionAction,
                Literal("unresolved"),
            )
        )
        graph.add(
            (
                disposition,
                UAD_SCHEMA.sourceQName,
                Literal(expanded_name),
            )
        )
        graph.add(
            (
                disposition,
                UAD_SCHEMA.instancePath,
                Literal(path),
            )
        )


__all__ = [
    "INSTANCE_NAMESPACE",
    "RdfProjectionStage",
    "RdfProjector",
    "UAD_SCHEMA",
]
