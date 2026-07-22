from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from rdflib import Graph, Literal, Namespace
from rdflib.namespace import OWL, RDF, RDFS


XS = "{http://www.w3.org/2001/XMLSchema}"

UAD = Namespace("https://dynamicontology.com/uad36/ontology#")
UADSCHEMA = Namespace("https://dynamicontology.com/uad36/schema#")


@dataclass(frozen=True)
class ComplexTypeDefinition:
    type_name: str
    class_local_name: str
    documentation: str | None
    base_type_name: str | None


def local_name_from_text(text: str) -> str:
    candidate = re.sub(r"[^A-Za-z0-9_]", "_", text.strip())

    if not candidate:
        raise ValueError(f"Cannot mint local name from text: {text!r}")

    if candidate[0].isdigit():
        candidate = f"_{candidate}"

    return candidate


def class_name_from_type_name(type_name: str) -> str:
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


def _strip_namespace_prefix(name: str | None) -> str | None:
    if not name:
        return None
    return name.split(":", 1)[-1]


def _base_type_name(complex_type: ET.Element) -> str | None:
    extension = complex_type.find(f".//{XS}extension")
    if extension is not None:
        return _strip_namespace_prefix(extension.attrib.get("base"))

    restriction = complex_type.find(f".//{XS}restriction")
    if restriction is not None:
        return _strip_namespace_prefix(restriction.attrib.get("base"))

    return None


def extract_complex_types_from_xsd(
    xsd_path: str | Path,
) -> list[ComplexTypeDefinition]:
    path = Path(xsd_path)
    tree = ET.parse(path)
    root = tree.getroot()

    complex_types: list[ComplexTypeDefinition] = []

    for complex_type in root.findall(f".//{XS}complexType"):
        type_name = complex_type.attrib.get("name")
        if not type_name:
            continue

        class_name = class_name_from_type_name(type_name)

        complex_types.append(
            ComplexTypeDefinition(
                type_name=type_name,
                class_local_name=local_name_from_text(class_name),
                documentation=_documentation_text(complex_type),
                base_type_name=_base_type_name(complex_type),
            )
        )

    return complex_types


def build_complex_type_vocabulary_graph(
    complex_types: list[ComplexTypeDefinition],
) -> Graph:
    graph = Graph()

    graph.bind("uad", UAD)
    graph.bind("uadschema", UADSCHEMA)
    graph.bind("owl", OWL)
    graph.bind("rdf", RDF)
    graph.bind("rdfs", RDFS)

    for complex_type in complex_types:
        class_iri = UADSCHEMA[complex_type.class_local_name]

        graph.add((class_iri, RDF.type, OWL.Class))
        graph.add((class_iri, RDF.type, UAD.SchemaComponent))
        graph.add((class_iri, RDFS.label, Literal(complex_type.class_local_name)))
        graph.add((class_iri, UAD.sourceComplexTypeName, Literal(complex_type.type_name)))

        if complex_type.documentation:
            graph.add((class_iri, RDFS.comment, Literal(complex_type.documentation)))

        if complex_type.base_type_name:
            base_class_name = class_name_from_type_name(complex_type.base_type_name)
            base_class_iri = UADSCHEMA[local_name_from_text(base_class_name)]
            graph.add((class_iri, RDFS.subClassOf, base_class_iri))
            graph.add((class_iri, UAD.sourceBaseTypeName, Literal(complex_type.base_type_name)))

    return graph


def generate_complex_type_vocabulary_ttl(
    xsd_path: str | Path,
    output_path: str | Path,
) -> None:
    complex_types = extract_complex_types_from_xsd(xsd_path)
    graph = build_complex_type_vocabulary_graph(complex_types)

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    graph.serialize(destination=str(output), format="turtle")


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate OWL classes from XSD complexType definitions."
    )
    parser.add_argument("xsd_path")
    parser.add_argument("output_path")

    args = parser.parse_args()

    generate_complex_type_vocabulary_ttl(
        xsd_path=args.xsd_path,
        output_path=args.output_path,
    )


if __name__ == "__main__":
    main()