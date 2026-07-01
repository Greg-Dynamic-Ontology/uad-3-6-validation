from __future__ import annotations

import re

from rdflib import URIRef

from app.core.namespaces import UAD_NAMESPACE


_LOCAL_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def is_valid_local_name(local_name: object) -> bool:
    if not isinstance(local_name, str):
        return False

    return bool(_LOCAL_NAME_PATTERN.fullmatch(local_name))


def mint_term_iri(local_name: str) -> URIRef:
    if not isinstance(local_name, str):
        raise TypeError("local_name must be a string")

    if not is_valid_local_name(local_name):
        raise ValueError(f"Invalid RDF local name: {local_name!r}")

    return URIRef(f"{UAD_NAMESPACE}{local_name}")