from pathlib import Path

from rdflib import Graph, Literal, Namespace, RDF, URIRef, XSD


PROJECT_ROOT = Path(__file__).resolve().parents[1]

CONSTRAINT_FILE = (
    PROJECT_ROOT
    / "ontologies"
    / "constraints"
    / "instances"
    / "0100.0007.ttl"
)

CONSTRAINT_VOCAB = Namespace(
    "https://dynamicontology.com/uad36/constraint-vocabulary#"
)

NORMALIZED_CONSTRAINT = URIRef(
    "https://dynamicontology.com/uad36/constraint/0100.0007"
)

ADDRESS_LINE_TEXT_QNAME = URIRef(
    "https://dynamicontology.com/uad36/logical-schema/qname/"
    "%7Bhttp%3A%2F%2Fwww.mismo.org%2Fresidential%2F2009%2Fschemas%7D"
    "AddressLineText"
)


def test_it_32_r1_c1_states_required_presence_behavior() -> None:
    assert CONSTRAINT_FILE.is_file()

    graph = Graph()
    graph.parse(CONSTRAINT_FILE, format="turtle")

    assert (
        NORMALIZED_CONSTRAINT,
        CONSTRAINT_VOCAB.behavior,
        CONSTRAINT_VOCAB.RequiredPresence,
    ) in graph

    assert (
        NORMALIZED_CONSTRAINT,
        CONSTRAINT_VOCAB.constrainsDataPoint,
        ADDRESS_LINE_TEXT_QNAME,
    ) in graph

    assert (
        NORMALIZED_CONSTRAINT,
        CONSTRAINT_VOCAB.minimumOccurrences,
        Literal(1, datatype=XSD.nonNegativeInteger),
    ) in graph

    assert (
        NORMALIZED_CONSTRAINT,
        CONSTRAINT_VOCAB.violationKind,
        CONSTRAINT_VOCAB.MissingRequiredValue,
    ) in graph

    assert (
        CONSTRAINT_VOCAB.RequiredPresence,
        RDF.type,
        CONSTRAINT_VOCAB.ConstraintBehavior,
    ) in graph

    assert (
        CONSTRAINT_VOCAB.MissingRequiredValue,
        RDF.type,
        CONSTRAINT_VOCAB.ViolationKind,
    ) in graph
