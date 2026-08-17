"""Project the Logical Schema Model into the UAD ontology."""

from rdflib import Graph, RDF
from rdflib.namespace import OWL

from app.generators.complex_type_vocabulary import (
    UADSCHEMA,
    class_name_from_type_name,
    local_name_from_text,
)
from app.models.schema_model import SchemaModel


def project_logical_schema_to_ontology(model: SchemaModel) -> Graph:
    """Project represented schema components into an RDF ontology graph."""

    graph = Graph()
    graph.bind("owl", OWL)
    graph.bind("uadschema", UADSCHEMA)

    for complex_type in model.complex_types.values():
        class_name = class_name_from_type_name(
            complex_type.name.local_name
        )
        class_iri = UADSCHEMA[local_name_from_text(class_name)]
        graph.add((class_iri, RDF.type, OWL.Class))

    return graph
