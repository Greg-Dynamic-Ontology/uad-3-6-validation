from pathlib import Path

from rdflib import Graph, Literal, Namespace, RDF, URIRef


PROJECT_ROOT = Path(__file__).resolve().parents[1]

CONSTRAINT_FILE = (
    PROJECT_ROOT
    / "ontologies"
    / "constraints"
    / "instances"
    / "0100.0007.old.ttl"
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

ADDRESS_LINE_TEXT_QNAME = URIRef(
    "https://dynamicontology.com/uad36/logical-schema/qname/"
    "%7Bhttp%3A%2F%2Fwww.mismo.org%2Fresidential%2F2009%2Fschemas%7D"
    "AddressLineText"
)

MISMO_NAMESPACE = "http://www.mismo.org/residential/2009/schemas"
ADDRESS_LINE_TEXT = "AddressLineText"


def test_it_32_r1_c1_binds_to_address_line_text_in_logical_schema() -> None:
    assert CONSTRAINT_FILE.is_file()
    assert LOGICAL_SCHEMA_FILE.is_file()

    constraint_graph = Graph()
    constraint_graph.parse(CONSTRAINT_FILE, format="turtle")

    logical_schema_graph = Graph()
    logical_schema_graph.parse(LOGICAL_SCHEMA_FILE, format="turtle")

    assert (
        ADDRESS_LINE_TEXT_QNAME,
        RDF.type,
        LOGICAL_SCHEMA.QName,
    ) in logical_schema_graph

    assert (
        ADDRESS_LINE_TEXT_QNAME,
        LOGICAL_SCHEMA.namespace,
        Literal(MISMO_NAMESPACE),
    ) in logical_schema_graph

    assert (
        ADDRESS_LINE_TEXT_QNAME,
        LOGICAL_SCHEMA.local_name,
        Literal(ADDRESS_LINE_TEXT),
    ) in logical_schema_graph

    assert (
        NORMALIZED_CONSTRAINT,
        CONSTRAINT_VOCAB.constrainsDataPoint,
        ADDRESS_LINE_TEXT_QNAME,
    ) in constraint_graph
