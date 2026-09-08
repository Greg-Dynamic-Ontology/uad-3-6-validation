"""IT-32R1C1 SHACL representation acceptance tests."""

from pathlib import Path

from pyshacl import validate
from rdflib import Graph, Namespace, RDF, URIRef


PROJECT_ROOT = Path(__file__).resolve().parents[1]

SHAPE_FILE = (
    PROJECT_ROOT
    / "ontologies"
    / "constraints"
    / "shapes"
    / "0100.0007.ttl"
)

FIXTURE_DIR = (
    PROJECT_ROOT
    / "tests"
    / "fixtures"
    / "constraints"
    / "it_32_r1_c1"
)

CONFORMING_FIXTURE = FIXTURE_DIR / "conforming.ttl"
VIOLATING_FIXTURE = FIXTURE_DIR / "violating.ttl"
UNRELATED_ADDRESS_FIXTURE = FIXTURE_DIR / "unrelated-address.ttl"

CONSTRAINT_VOCAB = Namespace(
    "https://dynamicontology.com/uad36/constraint-vocabulary#"
)

NORMALIZED_CONSTRAINT = URIRef(
    "https://dynamicontology.com/uad36/constraint/0100.0007"
)


def _load_graph(path: Path) -> Graph:
    graph = Graph()
    graph.parse(location=path.as_uri(), format="turtle")
    return graph


def _validate(data_file: Path) -> tuple[bool, Graph, str]:
    return validate(
        data_graph=_load_graph(data_file),
        shacl_graph=_load_graph(SHAPE_FILE),
        inference="none",
        abort_on_first=False,
        allow_infos=True,
        allow_warnings=True,
    )


def test_it_32_r1_c1_shacl_representation_exists_and_is_bound_to_constraint() -> None:
    assert SHAPE_FILE.is_file(), (
        "IT-32R1C1 requires a SHACL representation at "
        f"{SHAPE_FILE}"
    )

    shapes_graph = _load_graph(SHAPE_FILE)

    implementing_shapes = set(
        shapes_graph.subjects(
            CONSTRAINT_VOCAB.implementsConstraint,
            NORMALIZED_CONSTRAINT,
        )
    )

    assert len(implementing_shapes) == 1

    shape = implementing_shapes.pop()
    assert (
        shape,
        RDF.type,
        URIRef("http://www.w3.org/ns/shacl#NodeShape"),
    ) in shapes_graph


def test_it_32_r1_c1_shacl_accepts_required_address_line_text() -> None:
    assert SHAPE_FILE.is_file(), (
        "IT-32R1C1 requires a SHACL representation at "
        f"{SHAPE_FILE}"
    )
    assert CONFORMING_FIXTURE.is_file()

    conforms, _, _ = _validate(CONFORMING_FIXTURE)

    assert conforms is True


def test_it_32_r1_c1_shacl_rejects_missing_address_line_text() -> None:
    assert SHAPE_FILE.is_file(), (
        "IT-32R1C1 requires a SHACL representation at "
        f"{SHAPE_FILE}"
    )
    assert VIOLATING_FIXTURE.is_file()

    conforms, _, _ = _validate(VIOLATING_FIXTURE)

    assert conforms is False


def test_it_32_r1_c1_shacl_ignores_address_outside_subject_property_context() -> None:
    assert SHAPE_FILE.is_file(), (
        "IT-32R1C1 requires a SHACL representation at "
        f"{SHAPE_FILE}"
    )
    assert UNRELATED_ADDRESS_FIXTURE.is_file()

    conforms, _, _ = _validate(UNRELATED_ADDRESS_FIXTURE)

    assert conforms is True