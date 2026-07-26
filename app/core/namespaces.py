"""Shared namespace constants for the UAD 3.6 validation project."""

from __future__ import annotations

from rdflib import Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS

#
# UAD Ontology
#

UAD_ONTOLOGY_IRI = "https://dynamicontology.com/uad36/ontology"
UAD_NAMESPACE_IRI = UAD_ONTOLOGY_IRI + "#"
UAD_NAMESPACE = UAD_NAMESPACE_IRI

# Backward-compatible alias expected by ontology-loading tests.
ONTOLOGY_DOCUMENT_IRI = UAD_ONTOLOGY_IRI

UAD = Namespace(UAD_NAMESPACE_IRI)

#
# Schema Model
#

SCHEMA_MODEL_NAMESPACE_IRI = (
    "https://dynamicontology.com/uad36/schema-model#"
)

SCHEMA_MODEL = Namespace(SCHEMA_MODEL_NAMESPACE_IRI)

__all__ = [
    "OWL",
    "RDF",
    "RDFS",
    "URIRef",

    "UAD",
    "UAD_ONTOLOGY_IRI",
    "UAD_NAMESPACE_IRI",
    "ONTOLOGY_DOCUMENT_IRI",

    "SCHEMA_MODEL",
    "SCHEMA_MODEL_NAMESPACE_IRI",
]