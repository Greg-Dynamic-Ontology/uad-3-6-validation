from pathlib import Path

from rdflib import Graph, Literal, Namespace, RDF, URIRef


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONSTRAINT_FILE = PROJECT_ROOT / "ontologies" / "constraints" / "instances" / "0100.0007.old.ttl"

CONSTRAINT_VOCAB = Namespace("https://dynamicontology.com/uad36/constraint-vocabulary#")
PROV = Namespace("http://www.w3.org/ns/prov#")

NORMALIZED_CONSTRAINT = URIRef("https://dynamicontology.com/uad36/constraint/0100.0007")
SOURCE_CONSTRAINT = URIRef(
    "https://dynamicontology.com/uad36/source/umdp/fannie-mae/constraint/0100.0007"
)
UMDP_RULE = URIRef(
    "https://dynamicontology.com/uad36/source/umdp/fannie-mae/rule/UAD1001"
)

DATA_POINT_NAME = "AddressLineText"
REQUIREMENT_TEXT = "Provide the address line for the subject property physical address."
VIOLATION_CONDITION = "If AddressLineText is not provided"
SEVERITY = "Fatal"


def test_it_32_r1_c1_preserves_governed_constraint_knowledge() -> None:
    assert CONSTRAINT_FILE.is_file(), (
        "IT-32R1C1 requires a normalized governed constraint RDF artifact at "
        f"{CONSTRAINT_FILE}"
    )

    graph = Graph()
    graph.parse(CONSTRAINT_FILE, format="turtle")

    assert (
        NORMALIZED_CONSTRAINT,
        RDF.type,
        CONSTRAINT_VOCAB.GovernedConstraint,
    ) in graph

    assert (
        NORMALIZED_CONSTRAINT,
        CONSTRAINT_VOCAB.sourceConstraint,
        SOURCE_CONSTRAINT,
    ) in graph

    assert (
        NORMALIZED_CONSTRAINT,
        CONSTRAINT_VOCAB.umdpRule,
        UMDP_RULE,
    ) in graph

    assert (
        NORMALIZED_CONSTRAINT,
        CONSTRAINT_VOCAB.dataPointName,
        Literal(DATA_POINT_NAME),
    ) in graph

    assert (
        NORMALIZED_CONSTRAINT,
        CONSTRAINT_VOCAB.requirement,
        Literal(REQUIREMENT_TEXT),
    ) in graph

    assert (
        NORMALIZED_CONSTRAINT,
        CONSTRAINT_VOCAB.violationCondition,
        Literal(VIOLATION_CONDITION),
    ) in graph

    assert (
        NORMALIZED_CONSTRAINT,
        CONSTRAINT_VOCAB.severity,
        Literal(SEVERITY),
    ) in graph

    assert (
        NORMALIZED_CONSTRAINT,
        PROV.wasDerivedFrom,
        SOURCE_CONSTRAINT,
    ) in graph
