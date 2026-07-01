"""Tests for UAD 3.6 IRI minting policy.

These tests match the actual project package layout:

    app/core/namespaces.py
    app/core/iri_minting.py

They intentionally test public behavior, not implementation details.
"""

from __future__ import annotations

import pytest
from rdflib import Namespace, URIRef

from app.core.namespaces import UAD, UAD_ONTOLOGY_IRI
from app.core.iri_minting import mint_term_iri


EXPECTED_ONTOLOGY_IRI = "https://dynamicontology.com/uad36/ontology"
EXPECTED_NAMESPACE_IRI = "https://dynamicontology.com/uad36/ontology#"


def test_ontology_namespace_constant() -> None:
    assert str(UAD) == EXPECTED_NAMESPACE_IRI


def test_ontology_document_iri_constant() -> None:
    assert UAD_ONTOLOGY_IRI == EXPECTED_ONTOLOGY_IRI


def test_uad_namespace_is_rdflib_namespace() -> None:
    assert isinstance(UAD, Namespace)


def test_mint_term_iri_creates_uri_ref() -> None:
    iri = mint_term_iri("Attribute")

    assert isinstance(iri, URIRef)
    assert str(iri) == EXPECTED_NAMESPACE_IRI + "Attribute"


def test_mint_term_iri_is_deterministic() -> None:
    assert mint_term_iri("Attribute") == mint_term_iri("Attribute")


@pytest.mark.parametrize(
    "local_name",
    [
        "Attribute",
        "DataPoint",
        "Document",
        "LoanIdentifier",
        "x123",
    ],
)
def test_valid_local_names_are_accepted(local_name: str) -> None:
    assert str(mint_term_iri(local_name)) == EXPECTED_NAMESPACE_IRI + local_name


@pytest.mark.parametrize(
    "local_name",
    [
        "",
        " ",
        "Attribute Name",
        "Attribute/Name",
        "Attribute#Name",
        "123Attribute",
        "-Attribute",
        "Attribute.Name",
    ],
)
def test_invalid_local_names_are_rejected(local_name: str) -> None:
    with pytest.raises(ValueError):
        mint_term_iri(local_name)


def test_mint_term_iri_rejects_non_string_local_name() -> None:
    with pytest.raises(TypeError):
        mint_term_iri(None)  # type: ignore[arg-type]
