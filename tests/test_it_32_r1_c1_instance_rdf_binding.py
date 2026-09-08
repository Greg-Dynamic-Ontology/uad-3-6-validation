"""IT-32R1C1 instance RDF binding tests."""

from rdflib import Literal, RDF, URIRef

from app.services.rdf_projection import RdfProjector


MISMO_NAMESPACE = "http://www.mismo.org/residential/2009/schemas"
INSTANCE_NAMESPACE = "https://dynamicontology.com/uad36/instance/"

PROPERTY_CLASS_IRI = URIRef(f"{MISMO_NAMESPACE}PROPERTY")
ADDRESS_CLASS_IRI = URIRef(f"{MISMO_NAMESPACE}ADDRESS")

ADDRESS_PROPERTY_IRI = URIRef(f"{MISMO_NAMESPACE}ADDRESS")
ADDRESS_LINE_TEXT_PROPERTY_IRI = URIRef(
    f"{MISMO_NAMESPACE}AddressLineText"
)

SOURCE_NAME = "it-32-r1-c1.xml"

PROPERTY_RESOURCE = URIRef(
    f"{INSTANCE_NAMESPACE}{SOURCE_NAME}#PROPERTY"
)
ADDRESS_RESOURCE = URIRef(
    f"{INSTANCE_NAMESPACE}{SOURCE_NAME}#PROPERTY/ADDRESS-1"
)

ADDRESS_LINE_TEXT_VALUE = Literal("123 Main Street")


def test_it_32_r1_c1_projects_subject_property_address_for_validation() -> None:
    xml_bytes = f"""<?xml version="1.0" encoding="UTF-8"?>
<PROPERTY xmlns="{MISMO_NAMESPACE}">
    <ADDRESS>
        <AddressLineText>123 Main Street</AddressLineText>
    </ADDRESS>
</PROPERTY>
""".encode("utf-8")

    graph = RdfProjector().project(
        xml_bytes=xml_bytes,
        source_name=SOURCE_NAME,
    )

    assert (
        PROPERTY_RESOURCE,
        RDF.type,
        PROPERTY_CLASS_IRI,
    ) in graph

    assert (
        PROPERTY_RESOURCE,
        ADDRESS_PROPERTY_IRI,
        ADDRESS_RESOURCE,
    ) in graph

    assert (
        ADDRESS_RESOURCE,
        RDF.type,
        ADDRESS_CLASS_IRI,
    ) in graph

    assert (
        ADDRESS_RESOURCE,
        ADDRESS_LINE_TEXT_PROPERTY_IRI,
        ADDRESS_LINE_TEXT_VALUE,
    ) in graph
