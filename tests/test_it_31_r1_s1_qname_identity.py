from rdflib import Literal, RDF, URIRef

from app.models.schema_model import (
    ElementDeclaration,
    QName,
    SchemaModel,
    SimpleTypeDefinition,
)
from app.services.logical_schema_serializer import (
    LOGICAL_SCHEMA,
    logical_schema_model_to_graph,
)


MISMO_NAMESPACE = "http://www.mismo.org/residential/2009/schemas"
ADDRESS_LINE_TEXT = "AddressLineText"


def _qname_identity(graph) -> URIRef:
    matches = {
        subject
        for subject in graph.subjects(RDF.type, LOGICAL_SCHEMA.QName)
        if (
            subject,
            LOGICAL_SCHEMA.namespace,
            Literal(MISMO_NAMESPACE),
        )
        in graph
        and (
            subject,
            LOGICAL_SCHEMA.local_name,
            Literal(ADDRESS_LINE_TEXT),
        )
        in graph
    }

    assert len(matches) == 1
    identity = matches.pop()
    assert isinstance(identity, URIRef)
    return identity


def test_it_31_r1_s1_preserves_qname_using_governed_source_identity() -> None:
    qname = QName(
        namespace=MISMO_NAMESPACE,
        local_name=ADDRESS_LINE_TEXT,
    )

    element_model = SchemaModel(
        elements={
            qname: ElementDeclaration(name=qname),
        }
    )
    simple_type_model = SchemaModel(
        simple_types={
            qname: SimpleTypeDefinition(name=qname),
        }
    )

    element_graph = logical_schema_model_to_graph(element_model)
    simple_type_graph = logical_schema_model_to_graph(simple_type_model)

    element_identity = _qname_identity(element_graph)
    simple_type_identity = _qname_identity(simple_type_graph)

    assert element_identity == simple_type_identity
    assert ADDRESS_LINE_TEXT in str(element_identity)
    assert not str(element_identity).startswith(
        f"{LOGICAL_SCHEMA}resource-"
    )