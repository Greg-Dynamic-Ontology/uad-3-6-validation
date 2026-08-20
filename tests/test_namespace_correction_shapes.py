"""Ontology acceptance test for IT-9R1S2 conformance shapes."""

from pathlib import Path
import sys
from types import FrameType
from typing import Any

import app
from pyshacl import validate
from rdflib import Graph, Namespace, URIRef


PROJECT_ROOT = Path(app.__file__).resolve().parents[1]
SHAPES_FILE = (
    PROJECT_ROOT
    / "operators"
    / "namespace_correction"
    / "shapes.ttl"
)

OWB_OPERATOR = Namespace(
    "https://dynamicontology.com/owb/operator#"
)
LOGICAL_SCHEMA = Namespace(
    "https://dynamicontology.com/uad36/logical-schema#"
)
EXAMPLE = Namespace("https://dynamicontology.com/test/")

INPUT_SHAPE = OWB_OPERATOR.NamespaceCorrectionInputShape
OUTPUT_SHAPE = OWB_OPERATOR.NamespaceCorrectionOutputShape
OPERATOR_MODULE = "operators.namespace_correction.operator"

VALID_DIGEST = "a" * 64
VALID_PROVISIONAL_IRI = URIRef(
    "https://dynamicontology.com/owb/schema-source/sha256/"
    f"{VALID_DIGEST}"
)
MALFORMED_PROVISIONAL_IRI = URIRef(
    "https://dynamicontology.com/owb/schema-source/sha256/"
    "not-a-sha256-digest"
)
VALID_GOVERNED_IRI = URIRef(
    "https://dynamicontology.com/uad36/source/sha256/"
    f"{VALID_DIGEST}"
)


def _load_shapes() -> Graph:
    """Load the conformance shapes without importing operator.py."""

    assert SHAPES_FILE.is_file(), (
        "IT-9R1S2 requires independent namespace-correction shapes at "
        f"{SHAPES_FILE}."
    )

    shapes = Graph()
    shapes.parse(SHAPES_FILE, format="turtle")
    return shapes


def _source_reference_graph(source_iri: URIRef) -> Graph:
    """Build one non-vacuous graph containing a schema-source reference."""

    graph = Graph()
    graph.add(
        (
            EXAMPLE.schemaComponent,
            LOGICAL_SCHEMA.source_document,
            source_iri,
        )
    )
    return graph


def _validate_fixture(
    data_graph: Graph,
    shapes_graph: Graph,
    shape: URIRef,
) -> tuple[bool, str]:
    """Validate one fixture while detecting operator implementation calls."""

    operator_calls: list[str] = []
    prior_profiler = sys.getprofile()

    def record_operator_calls(
        frame: FrameType,
        event: str,
        arg: Any,
    ) -> None:
        del arg
        if (
            event == "call"
            and frame.f_globals.get("__name__") == OPERATOR_MODULE
        ):
            operator_calls.append(frame.f_code.co_name)

    sys.setprofile(record_operator_calls)
    try:
        conforms, _, report_text = validate(
            data_graph,
            shacl_graph=shapes_graph,
            inference="none",
            advanced=False,
            use_shapes=[shape],
        )
    finally:
        sys.setprofile(prior_profiler)

    assert not operator_calls, (
        "SHACL validation executed the namespace-correction "
        f"implementation: {operator_calls}"
    )
    return bool(conforms), str(report_text)


def test_input_and_output_requirements_validate_independently() -> None:
    """IT-9R1S2: Shapes accept and reject the four required fixtures."""

    shapes = _load_shapes()
    valid_input = _source_reference_graph(VALID_PROVISIONAL_IRI)
    malformed_input = _source_reference_graph(
        MALFORMED_PROVISIONAL_IRI
    )
    valid_output = _source_reference_graph(VALID_GOVERNED_IRI)
    invalid_output = _source_reference_graph(
        VALID_PROVISIONAL_IRI
    )

    valid_input_result = _validate_fixture(
        valid_input,
        shapes,
        INPUT_SHAPE,
    )
    malformed_input_result = _validate_fixture(
        malformed_input,
        shapes,
        INPUT_SHAPE,
    )
    valid_output_result = _validate_fixture(
        valid_output,
        shapes,
        OUTPUT_SHAPE,
    )
    invalid_output_result = _validate_fixture(
        invalid_output,
        shapes,
        OUTPUT_SHAPE,
    )

    assert valid_input_result[0], valid_input_result[1]
    assert not malformed_input_result[0]
    assert valid_output_result[0], valid_output_result[1]
    assert not invalid_output_result[0]

