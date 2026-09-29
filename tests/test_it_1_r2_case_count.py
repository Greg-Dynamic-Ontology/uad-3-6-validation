"""OTDD contract: the future single-equality RDF suite contains 174 cases.

A missing data file is validated as an empty graph so the RED result comes
from SHACL cardinality validation, rather than file loading or collection.
An existing malformed file is not swallowed. No data is created by this test.
"""

from pathlib import Path

import app
from pyshacl import validate
from rdflib import Graph, Namespace, URIRef


ROOT = Path(app.__file__).resolve().parents[1]
DATA = ROOT / (
    "data/uad36-test-suite/tests/fixtures/single_equality/test-suite.ttl"
)
SHAPES = ROOT / "shacl-source/single_equality_case_count.shacl.ttl"
T = Namespace("urn:uad36:test-suite:vocab:")
SUITE = URIRef("urn:uad36:test-suite:single-equality")


def test_it_1_r2_single_equality_suite_has_174_cases():
    data = Graph()
    if DATA.exists():
        data.parse(DATA, format="turtle")
    shapes = Graph().parse(SHAPES, format="turtle")
    conforms, report_graph, report_text = validate(
        data_graph=data,
        shacl_graph=shapes,
        inference="none",
        meta_shacl=True,
        advanced=False,
    )
    actual = len(set(data.objects(SUITE, T.hasCase)))
    assert conforms, (
        f"IT-1R2: expected exactly 174 case records; found {actual}.\n"
        f"Data file: {DATA} (exists: {DATA.exists()})\n"
        f"{report_text}"
    )
