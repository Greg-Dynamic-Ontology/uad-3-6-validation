from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from rdflib import Graph, Literal, Namespace
from rdflib.namespace import OWL, RDF, RDFS, XSD


XS = "{http://www.w3.org/2001/XMLSchema}"

UAD = Namespace("https://dynamicontology.com/uad36/ontology#")
UADPRED = Namespace("https://dynamicontology.com/uad36/predicate#")


@dataclass(frozen=True)
class ArcroleDefinition:
    source_uri: str
    local_name: str
    documentation: str | None


def local_name_from_arcrole_uri(uri: str) -> str:
    candidate = uri.rstrip("/#").split("/")[-1].split("#")[-1].split(":")[-1]
    candidate = re.sub(r"[^A-Za-z0-9_]", "_", candidate)

    if not candidate:
        raise ValueError(f"Cannot mint local name from arcrole URI: {uri}")

    if candidate[0].isdigit():
        candidate = f"_{candidate}"

    return candidate


def label_from_local_name(local_name: str) -> str:
    return local_name.replace("_", " ")


def extract_arcroles_from_xsd(
    xsd_path: str | Path,
    simple_type_name: str = "ArcroleBase",
) -> list[ArcroleDefinition]:
    path = Path(xsd_path)
    tree = ET.parse(path)
    root = tree.getroot()

    simple_type = None

    for candidate in root.findall(f".//{XS}simpleType"):
        if candidate.attrib.get("name") == simple_type_name:
            simple_type = candidate
            break

    if simple_type is None:
        raise ValueError(f"Could not find xs:simpleType named {simple_type_name}")

    arcroles: list[ArcroleDefinition] = []

    for enumeration in simple_type.findall(f".//{XS}enumeration"):
        value = enumeration.attrib.get("value")
        if not value:
            continue

        docs = [
            doc.text.strip()
            for doc in enumeration.findall(f".//{XS}documentation")
            if doc.text and doc.text.strip()
        ]

        arcroles.append(
            ArcroleDefinition(
                source_uri=value,
                local_name=local_name_from_arcrole_uri(value),
                documentation="\n\n".join(docs) if docs else None,
            )
        )

    return arcroles


def build_arcrole_vocabulary_graph(
    arcroles: list[ArcroleDefinition],
) -> Graph:
    graph = Graph()

    graph.bind("uad", UAD)
    graph.bind("uadpred", UADPRED)
    graph.bind("owl", OWL)
    graph.bind("rdf", RDF)
    graph.bind("rdfs", RDFS)
    graph.bind("xsd", XSD)

    for arcrole in arcroles:
        predicate_iri = UADPRED[arcrole.local_name]

        graph.add((predicate_iri, RDF.type, OWL.ObjectProperty))
        graph.add((predicate_iri, RDF.type, UAD.RelationshipPredicate))
        graph.add((predicate_iri, RDFS.label, Literal(label_from_local_name(arcrole.local_name))))
        graph.add(
            (
                predicate_iri,
                UAD.sourceArcroleUri,
                Literal(arcrole.source_uri, datatype=XSD.anyURI),
            )
        )

        if arcrole.documentation:
            graph.add((predicate_iri, RDFS.comment, Literal(arcrole.documentation)))

    return graph


def generate_arcrole_vocabulary_ttl(
    xsd_path: str | Path,
    output_path: str | Path,
    simple_type_name: str = "ArcroleBase",
) -> None:
    arcroles = extract_arcroles_from_xsd(
        xsd_path=xsd_path,
        simple_type_name=simple_type_name,
    )
    graph = build_arcrole_vocabulary_graph(arcroles)

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    graph.serialize(destination=str(output), format="turtle")


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate RDF predicate vocabulary from XSD arcrole enumerations."
    )
    parser.add_argument("xsd_path")
    parser.add_argument("output_path")
    parser.add_argument("--simple-type-name", default="ArcroleBase")

    args = parser.parse_args()

    generate_arcrole_vocabulary_ttl(
        xsd_path=args.xsd_path,
        output_path=args.output_path,
        simple_type_name=args.simple_type_name,
    )


if __name__ == "__main__":
    main()