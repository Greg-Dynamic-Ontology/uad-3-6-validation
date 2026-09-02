from rdflib import RDF, URIRef

from app.models.schema_model import (
    ComplexTypeDefinition,
    ModelGroup,
    ModelGroupKind,
    QName,
    SchemaModel,
)
from app.services.logical_schema_serializer import (
    LOGICAL_SCHEMA,
    logical_schema_model_to_graph,
)


MISMO_NAMESPACE = "http://www.mismo.org/residential/2009/schemas"
TEST_TYPE_NAME = "TestComplexType"


def _generated_model_group_identity(graph) -> URIRef:
    matches = {
        subject
        for subject in graph.subjects(RDF.type, LOGICAL_SCHEMA.ModelGroup)
        if str(subject).startswith(f"{LOGICAL_SCHEMA}resource-")
    }

    assert len(matches) == 1

    identity = matches.pop()
    assert isinstance(identity, URIRef)
    return identity


def _model_with_unnamed_group() -> SchemaModel:
    type_name = QName(
        namespace=MISMO_NAMESPACE,
        local_name=TEST_TYPE_NAME,
    )

    model_group = ModelGroup(
        kind=ModelGroupKind.SEQUENCE,
    )

    complex_type = ComplexTypeDefinition(
        name=type_name,
        content=model_group,
    )

    return SchemaModel(
        complex_types={
            type_name: complex_type,
        },
    )


def test_it_31_r1_s3_reserves_generated_identity_for_unnamed_structure() -> None:
    first_graph = logical_schema_model_to_graph(
        _model_with_unnamed_group()
    )
    second_graph = logical_schema_model_to_graph(
        _model_with_unnamed_group()
    )

    first_identity = _generated_model_group_identity(first_graph)
    second_identity = _generated_model_group_identity(second_graph)

    assert first_identity == second_identity
    assert str(first_identity).startswith(
        f"{LOGICAL_SCHEMA}resource-"
    )