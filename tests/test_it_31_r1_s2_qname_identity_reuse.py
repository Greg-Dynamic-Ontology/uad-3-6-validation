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


def test_it_31_r1_s2_reuses_qname_identity_across_schema_contexts() -> None:
    element_qname = QName(
        namespace=MISMO_NAMESPACE,
        local_name=ADDRESS_LINE_TEXT,
    )
    simple_type_qname = QName(
        namespace=MISMO_NAMESPACE,
        local_name=ADDRESS_LINE_TEXT,
    )

    model = SchemaModel(
        elements={
            element_qname: ElementDeclaration(name=element_qname),
        },
        simple_types={
            simple_type_qname: SimpleTypeDefinition(name=simple_type_qname),
        },
    )

    graph = logical_schema_model_to_graph(model)

    qname_resources = {
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

    assert len(qname_resources) == 1

    identity = qname_resources.pop()
    assert isinstance(identity, URIRef)
    assert ADDRESS_LINE_TEXT in str(identity)