"""Project loaded XML instances into RDF graphs."""

from collections import defaultdict
from xml.etree import ElementTree
from xml.etree.ElementTree import Element

from rdflib import Graph, Literal, RDF, URIRef

from app.utilities.xml_names import split_expanded_name

from app.models.appraisal import LoadedAppraisal


INSTANCE_NAMESPACE = "https://dynamicontology.com/uad36/instance/"


class RdfProjectionStage:
    """Run RDF projection using an appraisal already loaded in memory."""

    def __init__(self, *, projector: object) -> None:
        self.projector = projector

    def run(
        self,
        *,
        loaded_appraisal: LoadedAppraisal,
    ) -> Graph:
        return self.projector.project(
            xml_bytes=loaded_appraisal.xml_bytes,
            source_name=loaded_appraisal.source_name,
        )


class RdfProjector:
    """Project an XML instance into an RDF instance graph."""

    def project(
        self,
        *,
        xml_bytes: bytes,
        source_name: str,
    ) -> Graph:
        """Project XML bytes into an RDF graph."""

        root = ElementTree.fromstring(xml_bytes)

        root_namespace, root_local_name = split_expanded_name(
            root.tag
        )

        graph = Graph()

        root_resource = URIRef(
            f"{INSTANCE_NAMESPACE}{source_name}#{root_local_name}"
        )
        root_class = URIRef(
            f"{root_namespace}{root_local_name}"
        )

        graph.add(
            (
                root_resource,
                RDF.type,
                root_class,
            )
        )

        self._project_attributes(
            graph=graph,
            element=root,
            resource=root_resource,
        )

        self._project_children(
            graph=graph,
            parent_element=root,
            parent_resource=root_resource,
            parent_path=root_local_name,
            source_name=source_name,
        )

        return graph

    @classmethod
    def _project_children(
        cls,
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
            child_namespace, child_local_name = (
                split_expanded_name(child.tag)
            )

            predicate = URIRef(
                f"{child_namespace}{child_local_name}"
            )

            if len(child) == 0:
                cls._project_leaf_element(
                    graph=graph,
                    parent_resource=parent_resource,
                    predicate=predicate,
                    child=child,
                )

                cls._project_attributes(
                    graph=graph,
                    element=child,
                    resource=parent_resource,
                )

                continue

            sibling_counts[child_local_name] += 1
            sibling_number = sibling_counts[child_local_name]

            child_path = (
                f"{parent_path}/"
                f"{child_local_name}-{sibling_number}"
            )
            child_resource = URIRef(
                f"{INSTANCE_NAMESPACE}{source_name}#{child_path}"
            )
            child_class = URIRef(
                f"{child_namespace}{child_local_name}"
            )

            graph.add(
                (
                    parent_resource,
                    predicate,
                    child_resource,
                )
            )
            graph.add(
                (
                    child_resource,
                    RDF.type,
                    child_class,
                )
            )

            cls._project_attributes(
                graph=graph,
                element=child,
                resource=child_resource,
            )

            cls._project_children(
                graph=graph,
                parent_element=child,
                parent_resource=child_resource,
                parent_path=child_path,
                source_name=source_name,
            )

    @classmethod
    def _project_attributes(
        cls,
        *,
        graph: Graph,
        element: Element,
        resource: URIRef,
    ) -> None:
        """Project namespace-qualified attributes as literal properties."""

        for attribute_name, attribute_value in element.attrib.items():
            if not attribute_name.startswith("{"):
                continue

            attribute_namespace, attribute_local_name = (
                split_expanded_name(attribute_name)
            )

            predicate = URIRef(
                f"{attribute_namespace}{attribute_local_name}"
            )

            graph.add(
                (
                    resource,
                    predicate,
                    Literal(attribute_value),
                )
            )

    @staticmethod
    def _project_leaf_element(
        *,
        graph: Graph,
        parent_resource: URIRef,
        predicate: URIRef,
        child: Element,
    ) -> None:
        """Project a leaf XML element as an RDF literal property."""

        text = child.text
        if text is None:
            return

        value = text.strip()
        if not value:
            return

        graph.add(
            (
                parent_resource,
                predicate,
                Literal(value),
            )
        )