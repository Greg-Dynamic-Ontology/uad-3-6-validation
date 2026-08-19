"""Mint stable IRIs for schema source documents."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from rdflib import URIRef


SCHEMA_SOURCE_IRI_PREFIX = (
    "https://dynamicontology.com/uad36/source/sha256/"
)


def mint_schema_source_iri(source_document: Path) -> URIRef:
    """Mint a content-addressed IRI from schema document bytes."""

    digest = sha256(source_document.read_bytes()).hexdigest()
    return URIRef(f"{SCHEMA_SOURCE_IRI_PREFIX}{digest}")


__all__ = [
    "SCHEMA_SOURCE_IRI_PREFIX",
    "mint_schema_source_iri",
]
