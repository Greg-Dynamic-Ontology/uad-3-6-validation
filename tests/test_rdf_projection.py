"""Tests for projecting a loaded XML instance into RDF."""

from rdflib import Graph, Literal, RDF, URIRef
from rdflib.compare import isomorphic

from app.services.rdf_projection import RdfProjector


UAD_NAMESPACE = "https://example.com/uad#"
INSTANCE_NAMESPACE = "https://dynamicontology.com/uad36/instance/"

MESSAGE_CLASS_IRI = URIRef(
    f"{UAD_NAMESPACE}MESSAGE"
)
APPRAISAL_CLASS_IRI = URIRef(
    f"{UAD_NAMESPACE}APPRAISAL"
)
APPRAISAL_PROPERTY_IRI = URIRef(
    f"{UAD_NAMESPACE}APPRAISAL"
)
IDENTIFIER_PROPERTY_IRI = URIRef(
    f"{UAD_NAMESPACE}IDENTIFIER"
)
STATUS_PROPERTY_IRI = URIRef(
    f"{UAD_NAMESPACE}status"
)
SOURCE_PROPERTY_IRI = URIRef(
    f"{UAD_NAMESPACE}source"
)


def test_rdf_projector_projects_loaded_xml_into_instance_graph() -> None:
    """Feature: IT-4R1S1"""
    """A loaded XML instance is projected into an RDF instance graph."""

    xml_bytes = f"""<?xml version="1.0" encoding="UTF-8"?>
<uad:MESSAGE xmlns:uad="{UAD_NAMESPACE}">
    <uad:APPRAISAL>
        <uad:IDENTIFIER>APPRAISAL-001</uad:IDENTIFIER>
    </uad:APPRAISAL>
</uad:MESSAGE>
""".encode("utf-8")

    graph = RdfProjector().project(
        xml_bytes=xml_bytes,
        source_name="appraisal.xml",
    )

    assert isinstance(graph, Graph)
    assert len(graph) > 0
    assert any(
        graph.triples(
            (
                None,
                RDF.type,
                MESSAGE_CLASS_IRI,
            )
        )
    )


def test_rdf_projector_projects_leaf_element_as_literal_property() -> None:
    """Feature: IT-4R2S1"""
    """A leaf XML element becomes an RDF literal property."""

    xml_bytes = f"""<?xml version="1.0" encoding="UTF-8"?>
<uad:MESSAGE xmlns:uad="{UAD_NAMESPACE}">
    <uad:IDENTIFIER>APPRAISAL-001</uad:IDENTIFIER>
</uad:MESSAGE>
""".encode("utf-8")

    graph = RdfProjector().project(
        xml_bytes=xml_bytes,
        source_name="appraisal.xml",
    )

    assert any(
        graph.triples(
            (
                None,
                IDENTIFIER_PROPERTY_IRI,
                Literal("APPRAISAL-001"),
            )
        )
    )


def test_rdf_projector_projects_nested_element_as_linked_resource() -> None:
    """A nested XML element becomes a resource linked to its parent."""

    xml_bytes = f"""<?xml version="1.0" encoding="UTF-8"?>
<uad:MESSAGE xmlns:uad="{UAD_NAMESPACE}">
    <uad:APPRAISAL>
        <uad:IDENTIFIER>APPRAISAL-001</uad:IDENTIFIER>
    </uad:APPRAISAL>
</uad:MESSAGE>
""".encode("utf-8")

    graph = RdfProjector().project(
        xml_bytes=xml_bytes,
        source_name="appraisal.xml",
    )

    root_resource = URIRef(
        f"{INSTANCE_NAMESPACE}appraisal.xml#MESSAGE"
    )
    appraisal_resource = URIRef(
        f"{INSTANCE_NAMESPACE}appraisal.xml#MESSAGE/APPRAISAL-1"
    )

    assert (
        root_resource,
        APPRAISAL_PROPERTY_IRI,
        appraisal_resource,
    ) in graph

    assert (
        appraisal_resource,
        RDF.type,
        APPRAISAL_CLASS_IRI,
    ) in graph


def test_rdf_projector_preserves_nested_leaf_under_nested_resource() -> None:
    """Feature: IT-4R2S1"""
    """A nested leaf property belongs to its containing RDF resource."""

    xml_bytes = f"""<?xml version="1.0" encoding="UTF-8"?>
<uad:MESSAGE xmlns:uad="{UAD_NAMESPACE}">
    <uad:APPRAISAL>
        <uad:IDENTIFIER>APPRAISAL-001</uad:IDENTIFIER>
    </uad:APPRAISAL>
</uad:MESSAGE>
""".encode("utf-8")

    graph = RdfProjector().project(
        xml_bytes=xml_bytes,
        source_name="appraisal.xml",
    )

    root_resource = URIRef(
        f"{INSTANCE_NAMESPACE}appraisal.xml#MESSAGE"
    )
    appraisal_resource = URIRef(
        f"{INSTANCE_NAMESPACE}appraisal.xml#MESSAGE/APPRAISAL-1"
    )
    identifier = Literal("APPRAISAL-001")

    assert (
        appraisal_resource,
        IDENTIFIER_PROPERTY_IRI,
        identifier,
    ) in graph

    assert (
        root_resource,
        IDENTIFIER_PROPERTY_IRI,
        identifier,
    ) not in graph


def test_rdf_projector_projects_qualified_attribute_as_literal_property() -> None:
    """Feature: IT-4R2S1"""
    """A qualified XML attribute becomes an RDF literal property."""

    xml_bytes = f"""<?xml version="1.0" encoding="UTF-8"?>
<uad:MESSAGE
    xmlns:uad="{UAD_NAMESPACE}"
    uad:status="Complete">
</uad:MESSAGE>
""".encode("utf-8")

    graph = RdfProjector().project(
        xml_bytes=xml_bytes,
        source_name="appraisal.xml",
    )

    root_resource = URIRef(
        f"{INSTANCE_NAMESPACE}appraisal.xml#MESSAGE"
    )

    assert (
        root_resource,
        STATUS_PROPERTY_IRI,
        Literal("Complete"),
    ) in graph


def test_rdf_projector_assigns_unique_resources_to_repeated_sibling_elements(
) -> None:
    """Feature: IT-4R2S1"""
    """Repeated sibling XML elements become distinct from RDF resources."""

    xml_bytes = f"""<?xml version="1.0" encoding="UTF-8"?>
<uad:MESSAGE xmlns:uad="{UAD_NAMESPACE}">
    <uad:APPRAISAL>
        <uad:IDENTIFIER>APPRAISAL-001</uad:IDENTIFIER>
    </uad:APPRAISAL>
    <uad:APPRAISAL>
        <uad:IDENTIFIER>APPRAISAL-002</uad:IDENTIFIER>
    </uad:APPRAISAL>
</uad:MESSAGE>
""".encode("utf-8")

    graph = RdfProjector().project(
        xml_bytes=xml_bytes,
        source_name="appraisal.xml",
    )

    appraisal_1 = URIRef(
        f"{INSTANCE_NAMESPACE}appraisal.xml#MESSAGE/APPRAISAL-1"
    )
    appraisal_2 = URIRef(
        f"{INSTANCE_NAMESPACE}appraisal.xml#MESSAGE/APPRAISAL-2"
    )

    assert (
        appraisal_1,
        RDF.type,
        APPRAISAL_CLASS_IRI,
    ) in graph

    assert (
        appraisal_2,
        RDF.type,
        APPRAISAL_CLASS_IRI,
    ) in graph

    assert (
        appraisal_1,
        IDENTIFIER_PROPERTY_IRI,
        Literal("APPRAISAL-001"),
    ) in graph

    assert (
        appraisal_2,
        IDENTIFIER_PROPERTY_IRI,
        Literal("APPRAISAL-002"),
    ) in graph

    assert appraisal_1 != appraisal_2


def test_rdf_projector_preserves_attribute_on_leaf_element() -> None:
    """Feature: IT-4R2S1"""
    """A leaf element preserves both its value and qualified attributes."""

    xml_bytes = f"""<?xml version="1.0" encoding="UTF-8"?>
<uad:MESSAGE xmlns:uad="{UAD_NAMESPACE}">
    <uad:IDENTIFIER uad:source="ServiceLink">
        APPRAISAL-001
    </uad:IDENTIFIER>
</uad:MESSAGE>
""".encode("utf-8")

    graph = RdfProjector().project(
        xml_bytes=xml_bytes,
        source_name="appraisal.xml",
    )

    root_resource = URIRef(
        f"{INSTANCE_NAMESPACE}appraisal.xml#MESSAGE"
    )

    assert (
        root_resource,
        IDENTIFIER_PROPERTY_IRI,
        Literal("APPRAISAL-001"),
    ) in graph

    assert (
        root_resource,
        SOURCE_PROPERTY_IRI,
        Literal("ServiceLink"),
    ) in graph


def test_rdf_projector_reprojects_same_xml_as_equivalent_graph() -> None:
    """Feature: IT-4R5S1"""
    """Repeated projection of the same XML produces equivalent RDF."""

    xml_bytes = f"""<?xml version="1.0" encoding="UTF-8"?>
<uad:MESSAGE
    xmlns:uad="{UAD_NAMESPACE}"
    uad:status="Complete">
    <uad:APPRAISAL>
        <uad:IDENTIFIER uad:source="ServiceLink">
            APPRAISAL-001
        </uad:IDENTIFIER>
    </uad:APPRAISAL>
    <uad:APPRAISAL>
        <uad:IDENTIFIER>APPRAISAL-002</uad:IDENTIFIER>
    </uad:APPRAISAL>
</uad:MESSAGE>
""".encode("utf-8")

    first_graph = RdfProjector().project(
        xml_bytes=xml_bytes,
        source_name="appraisal.xml",
    )
    second_graph = RdfProjector().project(
        xml_bytes=xml_bytes,
        source_name="appraisal.xml",
    )

    assert isomorphic(first_graph, second_graph)
    assert len(first_graph) == len(second_graph)