"""Ontology acceptance test for IT-9R1S1 operator contract knowledge."""

from pathlib import Path

import app
from rdflib import Graph, Literal, Namespace, RDF, URIRef


PROJECT_ROOT = Path(app.__file__).resolve().parents[1]
OPERATOR_CONTRACT_FILE = (
    PROJECT_ROOT
    / "operators"
    / "namespace_correction"
    / "operator.ttl"
)

OWB_OPERATOR = Namespace(
    "https://dynamicontology.com/owb/operator#"
)
UAD_DECISION = Namespace(
    "https://dynamicontology.com/uad36/decision/"
)

CONTRACT = OWB_OPERATOR.NamespaceCorrectionContract
OPERATOR = OWB_OPERATOR.NamespaceCorrectionOperator
RDF_GRAPH = OWB_OPERATOR.RDFGraph

PROVISIONAL_SCHEMA_SOURCE_NAMESPACE = URIRef(
    "https://dynamicontology.com/owb/schema-source/sha256/"
)
GOVERNED_SCHEMA_SOURCE_NAMESPACE = URIRef(
    "https://dynamicontology.com/uad36/source/sha256/"
)


def _load_operator_contract() -> Graph:
    """Load the RDF contract without importing an operator implementation."""

    assert OPERATOR_CONTRACT_FILE.is_file(), (
        "IT-9R1S1 requires the governed namespace-correction contract at "
        f"{OPERATOR_CONTRACT_FILE}."
    )

    graph = Graph()
    graph.parse(OPERATOR_CONTRACT_FILE, format="turtle")
    return graph


def test_namespace_correction_is_a_governed_graph_operator() -> None:
    """IT-9R1S1: Describe namespace correction as governed RDF knowledge."""

    contract_graph = _load_operator_contract()

    required_statements = {
        (
            CONTRACT,
            RDF.type,
            OWB_OPERATOR.OperatorContract,
        ),
        (
            CONTRACT,
            OWB_OPERATOR.definesOperator,
            OPERATOR,
        ),
        (
            OPERATOR,
            RDF.type,
            OWB_OPERATOR.KnowledgeGraphOperator,
        ),
        (
            OPERATOR,
            OWB_OPERATOR.contract,
            CONTRACT,
        ),
        (
            CONTRACT,
            OWB_OPERATOR.inputType,
            RDF_GRAPH,
        ),
        (
            CONTRACT,
            OWB_OPERATOR.outputType,
            RDF_GRAPH,
        ),
        (
            CONTRACT,
            OWB_OPERATOR.sourceNamespace,
            PROVISIONAL_SCHEMA_SOURCE_NAMESPACE,
        ),
        (
            CONTRACT,
            OWB_OPERATOR.targetNamespace,
            GOVERNED_SCHEMA_SOURCE_NAMESPACE,
        ),
        (
            CONTRACT,
            OWB_OPERATOR.governedBy,
            UAD_DECISION["ADR-0017"],
        ),
        (
            CONTRACT,
            OWB_OPERATOR.governedBy,
            UAD_DECISION["ADR-0018"],
        ),
        (
            CONTRACT,
            OWB_OPERATOR.deterministic,
            Literal(True),
        ),
        (
            CONTRACT,
            OWB_OPERATOR.idempotent,
            Literal(True),
        ),
    }

    missing_statements = required_statements - set(contract_graph)
    assert not missing_statements, (
        "The namespace-correction RDF contract is missing required "
        f"governed knowledge: {sorted(map(str, missing_statements))}"
    )

    assert isinstance(OPERATOR, URIRef)
    assert str(OPERATOR).startswith(
        "https://dynamicontology.com/"
    )

