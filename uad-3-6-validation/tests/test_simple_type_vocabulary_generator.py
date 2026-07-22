from pathlib import Path

from rdflib import Graph, Literal, Namespace
from rdflib.namespace import RDF, RDFS, SKOS

from app.generators.simple_type_vocabulary import (
    extract_simple_type_enumerations_from_xsd,
    generate_simple_type_vocabulary_ttl,
    local_name_from_text,
    scheme_name_from_type_name,
)


UAD = Namespace("https://dynamicontology.com/uad36/ontology#")
UADVALUE = Namespace("https://dynamicontology.com/uad36/value#")


def test_local_name_from_text():
    assert local_name_from_text("C3") == "C3"
    assert local_name_from_text("Accessory Dwelling Unit") == "Accessory_Dwelling_Unit"
    assert local_name_from_text("123") == "_123"


def test_scheme_name_from_type_name():
    assert scheme_name_from_type_name("ConditionRatingType") == "ConditionRating"
    assert scheme_name_from_type_name("PropertyUsage") == "PropertyUsage"


def test_extract_simple_type_enumerations_from_xsd(tmp_path: Path):
    xsd_file = tmp_path / "sample.xsd"
    xsd_file.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
    <xs:simpleType name="ConditionRatingType">
        <xs:annotation>
            <xs:documentation>Condition rating values.</xs:documentation>
        </xs:annotation>
        <xs:restriction base="xs:string">
            <xs:enumeration value="C1">
                <xs:annotation>
                    <xs:documentation>Best condition.</xs:documentation>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="C2"/>
        </xs:restriction>
    </xs:simpleType>
</xs:schema>
""",
        encoding="utf-8",
    )

    simple_types = extract_simple_type_enumerations_from_xsd(xsd_file)

    assert len(simple_types) == 1
    assert simple_types[0].type_name == "ConditionRatingType"
    assert simple_types[0].scheme_local_name == "ConditionRating"
    assert simple_types[0].documentation == "Condition rating values."
    assert len(simple_types[0].values) == 2
    assert simple_types[0].values[0].value == "C1"
    assert simple_types[0].values[0].documentation == "Best condition."
    assert simple_types[0].values[1].value == "C2"


def test_generate_simple_type_vocabulary_ttl(tmp_path: Path):
    xsd_file = tmp_path / "sample.xsd"
    ttl_file = tmp_path / "values.ttl"

    xsd_file.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
    <xs:simpleType name="ConditionRatingType">
        <xs:restriction base="xs:string">
            <xs:enumeration value="C1">
                <xs:annotation>
                    <xs:documentation>Best condition.</xs:documentation>
                </xs:annotation>
            </xs:enumeration>
            <xs:enumeration value="C2"/>
        </xs:restriction>
    </xs:simpleType>
</xs:schema>
""",
        encoding="utf-8",
    )

    generate_simple_type_vocabulary_ttl(xsd_file, ttl_file)

    graph = Graph()
    graph.parse(ttl_file, format="turtle")

    scheme = UADVALUE.ConditionRating
    c1 = UADVALUE["ConditionRating-C1"]
    c2 = UADVALUE["ConditionRating-C2"]

    assert (scheme, RDF.type, SKOS.ConceptScheme) in graph
    assert (scheme, UAD.sourceSimpleTypeName, Literal("ConditionRatingType")) in graph

    assert (c1, RDF.type, SKOS.Concept) in graph
    assert (c1, SKOS.inScheme, scheme) in graph
    assert (c1, SKOS.prefLabel, Literal("C1")) in graph
    assert (c1, RDFS.comment, Literal("Best condition.")) in graph

    assert (c2, RDF.type, SKOS.Concept) in graph
    assert (c2, SKOS.inScheme, scheme) in graph