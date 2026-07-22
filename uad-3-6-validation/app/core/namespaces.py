"""Shared RDF namespace constants for the UAD 3.6 validation project."""

from __future__ import annotations

from rdflib import Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS

UAD_ONTOLOGY_IRI = "https://dynamicontology.com/uad36/ontology"
UAD_NAMESPACE_IRI = UAD_ONTOLOGY_IRI + "#"

# Backward-compatible alias expected by ontology-loading tests.
ONTOLOGY_DOCUMENT_IRI = UAD_ONTOLOGY_IRI

UAD = Namespace(UAD_NAMESPACE_IRI)
UAD_NAMESPACE = "https://dynamicontology.com/uad36/ontology#"
ONTOLOGY_DOCUMENT_IRI = "https://dynamicontology.com/uad36/ontology"

UAD = Namespace(UAD_NAMESPACE)
__all__ = [
    "OWL",
    "RDF",
    "RDFS",
    "UAD",
    "UAD_NAMESPACE_IRI",
    "UAD_ONTOLOGY_IRI",
    "ONTOLOGY_DOCUMENT_IRI",
    "URIRef",
]
