from pathlib import Path
from xml.etree import ElementTree

from rdflib import Graph, Namespace, RDF, RDFS, URIRef
from rdflib.namespace import OWL


XSD_NAMESPACE = "http://www.w3.org/2001/XMLSchema"
DEFAULT_RESOURCE_NAMESPACE = (
    "https://dynamicontology.com/otdd/examples/complexType-element#"
)


def project_xsd_to_rdf(xsd_path: Path) -> Graph:
    """
    Project the supported XSD constructs into an RDF schema graph.

    Currently supported:

    - global xsd:complexType -> owl:Class
    - global xsd:element -> owl:ObjectProperty
    - xsd:element/@type -> rdfs:range

    When the XSD has no targetNamespace, the configured example namespace is
    used as the resource namespace.
    """
    root = ElementTree.parse(xsd_path).getroot()

    target_namespace = root.get("targetNamespace")
    resource_namespace = Namespace(
        _with_fragment_separator(
            target_namespace or DEFAULT_RESOURCE_NAMESPACE
        )
    )

    graph = Graph()
    graph.bind("owl", OWL)
    graph.bind("rdfs", RDFS)
    graph.bind("example", resource_namespace)

    complex_type_tag = f"{{{XSD_NAMESPACE}}}complexType"
    element_tag = f"{{{XSD_NAMESPACE}}}element"

    for complex_type in root.findall(complex_type_tag):
        type_name = complex_type.get("name")
        if not type_name:
            continue

        graph.add(
            (
                URIRef(resource_namespace[type_name]),
                RDF.type,
                OWL.Class,
            )
        )

    for element in root.findall(element_tag):
        element_name = element.get("name")
        if not element_name:
            continue

        property_iri = URIRef(resource_namespace[element_name])

        graph.add(
            (
                property_iri,
                RDF.type,
                OWL.ObjectProperty,
            )
        )

        type_reference = element.get("type")
        if type_reference:
            local_type_name = _local_name(type_reference)
            graph.add(
                (
                    property_iri,
                    RDFS.range,
                    URIRef(resource_namespace[local_type_name]),
                )
            )

    return graph


def _local_name(qualified_name: str) -> str:
    """
    Return the local name from an XML QName.

    Examples:

    - AddressType -> AddressType
    - tns:AddressType -> AddressType
    """
    return qualified_name.rsplit(":", maxsplit=1)[-1]


def _with_fragment_separator(namespace: str) -> str:
    """
    Ensure locally minted resource IRIs are separated from the namespace IRI.
    """
    if namespace.endswith(("#", "/")):
        return namespace

    return f"{namespace}#"