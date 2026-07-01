from pathlib import Path

from rdflib import Graph, Literal, Namespace
from rdflib.namespace import OWL, RDF, RDFS

from app.generators.complex_type_vocabulary import (
    class_name_from_type_name,
    extract_complex_types_from_xsd,
    generate_complex_type_vocabulary_ttl,
    local_name_from_text,
)


UAD = Namespace("https://dynamicontology.com/uad36/ontology#")
UADSCHEMA = Namespace("https://dynamicontology.com/uad36/schema#")


def test_local_name_from_text():
    assert local_name_from_text("SubjectProperty") == "SubjectProperty"
    assert local_name_from_text("Subject Property") == "Subject_Property"
    assert local_name_from_text("123Type") == "_123Type"


def test_class_name_from_type_name():
    assert class_name_from_type_name("SubjectPropertyType") == "SubjectProperty"
    assert class_name_from_type_name("AppraisalReport") == "AppraisalReport"


def test_extract_complex_types_from_xsd(tmp_path: Path):
    xsd_file = tmp_path / "sample.xsd"
    xsd_file.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:mismo="urn:sample">
    <xs:complexType name="PropertyType">
        <xs:annotation>
            <xs:documentation>Represents a property.</xs:documentation>
        </xs:annotation>
        <xs:sequence/>
    </xs:complexType>

    <xs:complexType name="SubjectPropertyType">
        <xs:annotation>
            <xs:documentation>Represents the subject property.</xs:documentation>
        </xs:annotation>
        <xs:complexContent>
            <xs:extension base="mismo:PropertyType">
                <xs:sequence/>
            </xs:extension>
        </xs:complexContent>
    </xs:complexType>
</xs:schema>
""",
        encoding="utf-8",
    )

    complex_types = extract_complex_types_from_xsd(xsd_file)

    assert len(complex_types) == 2

    assert complex_types[0].type_name == "PropertyType"
    assert complex_types[0].class_local_name == "Property"
    assert complex_types[0].documentation == "Represents a property."
    assert complex_types[0].base_type_name is None

    assert complex_types[1].type_name == "SubjectPropertyType"
    assert complex_types[1].class_local_name == "SubjectProperty"
    assert complex_types[1].documentation == "Represents the subject property."
    assert complex_types[1].base_type_name == "PropertyType"


def test_generate_complex_type_vocabulary_ttl(tmp_path: Path):
    xsd_file = tmp_path / "sample.xsd"
    ttl_file = tmp_path / "complex-types.ttl"

    xsd_file.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:mismo="urn:sample">
    <xs:complexType name="PropertyType">
        <xs:annotation>
            <xs:documentation>Represents a property.</xs:documentation>
        </xs:annotation>
        <xs:sequence/>
    </xs:complexType>

    <xs:complexType name="SubjectPropertyType">
        <xs:annotation>
            <xs:documentation>Represents the subject property.</xs:documentation>
        </xs:annotation>
        <xs:complexContent>
            <xs:extension base="mismo:PropertyType">
                <xs:sequence/>
            </xs:extension>
        </xs:complexContent>
    </xs:complexType>
</xs:schema>
""",
        encoding="utf-8",
    )

    generate_complex_type_vocabulary_ttl(xsd_file, ttl_file)

    graph = Graph()
    graph.parse(ttl_file, format="turtle")

    property_class = UADSCHEMA.Property
    subject_property_class = UADSCHEMA.SubjectProperty

    assert (property_class, RDF.type, OWL.Class) in graph
    assert (property_class, RDF.type, UAD.SchemaComponent) in graph
    assert (property_class, UAD.sourceComplexTypeName, Literal("PropertyType")) in graph
    assert (property_class, RDFS.comment, Literal("Represents a property.")) in graph

    assert (subject_property_class, RDF.type, OWL.Class) in graph
    assert (subject_property_class, RDF.type, UAD.SchemaComponent) in graph
    assert (subject_property_class, UAD.sourceComplexTypeName, Literal("SubjectPropertyType")) in graph
    assert (subject_property_class, UAD.sourceBaseTypeName, Literal("PropertyType")) in graph
    assert (subject_property_class, RDFS.subClassOf, property_class) in graph