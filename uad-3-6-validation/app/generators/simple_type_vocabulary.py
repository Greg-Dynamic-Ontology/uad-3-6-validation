from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from rdflib import Graph, Literal, Namespace
from rdflib.namespace import RDF, RDFS, SKOS, XSD


XS = "{http://www.w3.org/2001/XMLSchema}"

UAD = Namespace("https://dynamicontology.com/uad36/ontology#")
UADVALUE = Namespace("https://dynamicontology.com/uad36/value#")


@dataclass(frozen=True)
class EnumerationValue:
    value: str
    local_name: str
    documentation: str | None


@dataclass(frozen=True)
class SimpleTypeEnumeration:
    type_name: str
    scheme_local_name: str
    values: list[EnumerationValue]
    documentation: str | None


def local_name_from_text(text: str) -> str:
    candidate = re.sub(r"[^A-Za-z0-9_]", "_", text.strip())

    if not candidate:
        raise ValueError(f"Cannot mint local name from text: {text!r}")

    if candidate[0].isdigit():
        candidate = f"_{candidate}"

    return candidate


def scheme_name_from_type_name(type_name: str) -> str:
    if type_name.endswith("Type"):
        return type_name[:-4]
    return type_name

def _documentation_text(element: ET.Element) -> str | None:
    docs = [
        doc.text.strip()
        for doc in element.findall(f"{XS}annotation/{XS}documentation")
        if doc.text and doc.text.strip()
    ]
    return "\n\n".join(docs) if docs else None


def extract_simple_type_enumerations_from_xsd(
    xsd_path: str | Path,
) -> list[SimpleTypeEnumeration]:
    path = Path(xsd_path)
    tree = ET.parse(path)
    root = tree.getroot()

    simple_types: list[SimpleTypeEnumeration] = []

    for simple_type in root.findall(f".//{XS}simpleType"):
        type_name = simple_type.attrib.get("name")
        if not type_name:
            continue

        enumerations = simple_type.findall(f".//{XS}enumeration")
        if not enumerations:
            continue

        values: list[EnumerationValue] = []

        for enumeration in enumerations:
            value = enumeration.attrib.get("value")
            if not value:
                continue

            values.append(
                EnumerationValue(
                    value=value,
                    local_name=local_name_from_text(value),
                    documentation=_documentation_text(enumeration),
                )
            )

        if values:
            scheme_name = scheme_name_from_type_name(type_name)

            simple_types.append(
                SimpleTypeEnumeration(
                    type_name=type_name,
                    scheme_local_name=local_name_from_text(scheme_name),
                    values=values,
                    documentation=_documentation_text(simple_type),
                )
            )

    return simple_types


def build_simple_type_vocabulary_graph(
    simple_types: list[SimpleTypeEnumeration],
) -> Graph:
    graph = Graph()

    graph.bind("uad", UAD)
    graph.bind("uadvalue", UADVALUE)
    graph.bind("rdf", RDF)
    graph.bind("rdfs", RDFS)
    graph.bind("skos", SKOS)
    graph.bind("xsd", XSD)

    for simple_type in simple_types:
        scheme_iri = UADVALUE[simple_type.scheme_local_name]

        graph.add((scheme_iri, RDF.type, SKOS.ConceptScheme))
        graph.add((scheme_iri, RDFS.label, Literal(simple_type.scheme_local_name)))
        graph.add((scheme_iri, SKOS.prefLabel, Literal(simple_type.scheme_local_name)))
        graph.add((scheme_iri, UAD.sourceSimpleTypeName, Literal(simple_type.type_name)))

        if simple_type.documentation:
            graph.add((scheme_iri, RDFS.comment, Literal(simple_type.documentation)))

        for value in simple_type.values:
            concept_iri = UADVALUE[f"{simple_type.scheme_local_name}-{value.local_name}"]

            graph.add((concept_iri, RDF.type, SKOS.Concept))
            graph.add((concept_iri, SKOS.inScheme, scheme_iri))
            graph.add((concept_iri, SKOS.prefLabel, Literal(value.value)))
            graph.add((concept_iri, UAD.sourceEnumerationValue, Literal(value.value)))

            if value.documentation:
                graph.add((concept_iri, RDFS.comment, Literal(value.documentation)))

    return graph


def generate_simple_type_vocabulary_ttl(
    xsd_path: str | Path,
    output_path: str | Path,
) -> None:
    simple_types = extract_simple_type_enumerations_from_xsd(xsd_path)
    graph = build_simple_type_vocabulary_graph(simple_types)

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    graph.serialize(destination=str(output), format="turtle")


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate SKOS vocabularies from XSD simpleType enumerations."
    )
    parser.add_argument("xsd_path")
    parser.add_argument("output_path")

    args = parser.parse_args()

    generate_simple_type_vocabulary_ttl(
        xsd_path=args.xsd_path,
        output_path=args.output_path,
    )


if __name__ == "__main__":
    main()