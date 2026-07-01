from pathlib import Path

from rdflib import Graph, Literal, Namespace
from rdflib.namespace import OWL, RDF, RDFS, XSD

from app.generators.arcrole_vocabulary import (
    extract_arcroles_from_xsd,
    generate_arcrole_vocabulary_ttl,
    local_name_from_arcrole_uri,
)


UAD = Namespace("https://dynamicontology.com/uad36/ontology#")
UADPRED = Namespace("https://dynamicontology.com/uad36/predicate#")


def test_local_name_from_arcrole_uri():
    uri = "urn:fdc:mismo.org:2009:residential/DATA_SOURCE_IsDataSourceFor_AccessoryDwellingUnitLegallyRentableIndicator"

    assert (
        local_name_from_arcrole_uri(uri)
        == "DATA_SOURCE_IsDataSourceFor_AccessoryDwellingUnitLegallyRentableIndicator"
    )


def test_extract_arcroles_from_xsd(tmp_path: Path):
    xsd_file = tmp_path / "sample.xsd"
    xsd_file.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
    <xs:simpleType name="ArcroleBase">
        <xs:restriction base="xs:anyURI">
            <xs:enumeration value="urn:fdc:mismo.org:2009:residential/DATA_SOURCE_IsDataSourceFor_AccessoryDwellingUnitLegallyRentableIndicator">
                <xs:annotation>
                    <xs:documentation>Link DATA_SOURCE to the item that needs a source of information identified.</xs:documentation>
                </xs:annotation>
            </xs:enumeration>
        </xs:restriction>
    </xs:simpleType>
</xs:schema>
""",
        encoding="utf-8",
    )

    arcroles = extract_arcroles_from_xsd(xsd_file)

    assert len(arcroles) == 1
    assert arcroles[0].source_uri == (
        "urn:fdc:mismo.org:2009:residential/"
        "DATA_SOURCE_IsDataSourceFor_AccessoryDwellingUnitLegallyRentableIndicator"
    )
    assert arcroles[0].local_name == "DATA_SOURCE_IsDataSourceFor_AccessoryDwellingUnitLegallyRentableIndicator"
    assert arcroles[0].documentation == "Link DATA_SOURCE to the item that needs a source of information identified."


def test_generate_arcrole_vocabulary_ttl(tmp_path: Path):
    xsd_file = tmp_path / "sample.xsd"
    ttl_file = tmp_path / "arcroles.ttl"

    xsd_file.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
    <xs:simpleType name="ArcroleBase">
        <xs:restriction base="xs:anyURI">
            <xs:enumeration value="urn:fdc:mismo.org:2009:residential/DATA_SOURCE_IsDataSourceFor_AccessoryDwellingUnitLegallyRentableIndicator">
                <xs:annotation>
                    <xs:documentation>Link DATA_SOURCE to the item that needs a source of information identified.</xs:documentation>
                </xs:annotation>
            </xs:enumeration>
        </xs:restriction>
    </xs:simpleType>
</xs:schema>
""",
        encoding="utf-8",
    )

    generate_arcrole_vocabulary_ttl(xsd_file, ttl_file)

    graph = Graph()
    graph.parse(ttl_file, format="turtle")

    predicate = UADPRED.DATA_SOURCE_IsDataSourceFor_AccessoryDwellingUnitLegallyRentableIndicator

    assert (predicate, RDF.type, OWL.ObjectProperty) in graph
    assert (predicate, RDF.type, UAD.RelationshipPredicate) in graph
    assert (
        predicate,
        UAD.sourceArcroleUri,
        Literal(
            "urn:fdc:mismo.org:2009:residential/"
            "DATA_SOURCE_IsDataSourceFor_AccessoryDwellingUnitLegallyRentableIndicator",
            datatype=XSD.anyURI,
        ),
    ) in graph
    assert (
        predicate,
        RDFS.comment,
        Literal("Link DATA_SOURCE to the item that needs a source of information identified."),
    ) in graph