from pathlib import Path

from rdflib import Graph, Namespace, RDF, URIRef
from rdflib.collection import Collection


PROJECT_ROOT = Path(__file__).resolve().parents[1]

CONSTRAINT_FILE = (
    PROJECT_ROOT
    / "ontologies"
    / "constraints"
    / "instances"
    / "0100.0007.ttl"
)

LOGICAL_SCHEMA_FILE = (
    PROJECT_ROOT
    / "docs"
    / "milestones"
    / "milestone-1"
    / "artifacts"
    / "logical-schema.ttl"
)

CONSTRAINT_VOCAB = Namespace(
    "https://dynamicontology.com/uad36/constraint-vocabulary#"
)
LOGICAL_SCHEMA = Namespace(
    "https://dynamicontology.com/uad36/logical-schema#"
)

NORMALIZED_CONSTRAINT = URIRef(
    "https://dynamicontology.com/uad36/constraint/0100.0007"
)

CONTEXT = URIRef(
    "https://dynamicontology.com/uad36/"
    "constraint/0100.0007/context/subject-property-address"
)

QNAME_BASE = (
    "https://dynamicontology.com/uad36/logical-schema/qname/"
    "%7Bhttp%3A%2F%2Fwww.mismo.org%2Fresidential%2F2009%2Fschemas%7D"
)

PROPERTY_QNAME = URIRef(f"{QNAME_BASE}PROPERTY")
ADDRESS_QNAME = URIRef(f"{QNAME_BASE}ADDRESS")
ADDRESS_LINE_TEXT_QNAME = URIRef(f"{QNAME_BASE}AddressLineText")


def _assert_qname_exists(graph: Graph, qname: URIRef) -> None:
    assert (
        qname,
        RDF.type,
        LOGICAL_SCHEMA.QName,
    ) in graph


def test_it_32_r1_c1_resolves_subject_property_address_context() -> None:
    assert CONSTRAINT_FILE.is_file()
    assert LOGICAL_SCHEMA_FILE.is_file()

    constraint_graph = Graph()
    constraint_graph.parse(CONSTRAINT_FILE, format="turtle")

    logical_schema_graph = Graph()
    logical_schema_graph.parse(LOGICAL_SCHEMA_FILE, format="turtle")

    _assert_qname_exists(logical_schema_graph, PROPERTY_QNAME)
    _assert_qname_exists(logical_schema_graph, ADDRESS_QNAME)
    _assert_qname_exists(logical_schema_graph, ADDRESS_LINE_TEXT_QNAME)

    assert (
        NORMALIZED_CONSTRAINT,
        CONSTRAINT_VOCAB.applicableContext,
        CONTEXT,
    ) in constraint_graph

    assert (
        CONTEXT,
        RDF.type,
        CONSTRAINT_VOCAB.ConstraintContext,
    ) in constraint_graph

    path_heads = list(
        constraint_graph.objects(
            CONTEXT,
            CONSTRAINT_VOCAB.schemaPath,
        )
    )
    assert len(path_heads) == 1

    schema_path = list(
        Collection(
            constraint_graph,
            path_heads[0],
        )
    )

    assert schema_path == [
        PROPERTY_QNAME,
        ADDRESS_QNAME,
        ADDRESS_LINE_TEXT_QNAME,
    ]
