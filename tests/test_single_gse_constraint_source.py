"""Acceptance tests for IT-30R1S2 single-GSE source evidence."""

from __future__ import annotations

from dataclasses import dataclass, field
from importlib import import_module
from typing import Any

import pytest


GSE_CONSTRAINT_SOURCES_MODULE = "app.services.gse_constraint_sources"


@dataclass(frozen=True)
class AuthoritativeGseConstraintSourceEvidence:
    source_document_name: str
    source_version: str
    issuing_authorities: frozenset[str]
    acquisition_location: str
    content_digest: str
    constraint_ids: tuple[str, ...]


@dataclass
class GseConstraintSourceRepositorySpy:
    saved_sources: list[object] = field(default_factory=list)

    def save(self, registered_source: object) -> None:
        self.saved_sources.append(registered_source)


def _single_gse_source_registration_contract() -> Any:
    """Load the governed source-registration contract for IT-30R1S2."""

    module = import_module(GSE_CONSTRAINT_SOURCES_MODULE)
    register_source = getattr(
        module,
        "register_authoritative_gse_constraint_source",
        None,
    )
    assert callable(register_source), (
        "IT-30R1S2 requires "
        "register_authoritative_gse_constraint_source("
        "source_evidence, repository)."
    )
    return register_source


@pytest.mark.parametrize(
    ("issuing_gse", "classification", "acquisition_location"),
    (
        (
            "fannie_mae",
            "fannie_mae_only",
            "specs/FannieMae/fannie-proprietary-rules.xlsx",
        ),
        (
            "freddie_mac",
            "freddie_mac_only",
            "specs/FreddieMac/freddie-proprietary-rules.xlsx",
        ),
    ),
    ids=("fannie-mae-only", "freddie-mac-only"),
)
def test_it_30_r1_s2_recognizes_a_source_issued_by_one_gse(
    issuing_gse: str,
    classification: str,
    acquisition_location: str,
) -> None:
    """Classify only the GSE named by explicit sole-issuer evidence."""

    register_source = _single_gse_source_registration_contract()
    source_evidence = AuthoritativeGseConstraintSourceEvidence(
        source_document_name=f"{issuing_gse} governed constraint rules",
        source_version="1.0",
        issuing_authorities=frozenset({issuing_gse}),
        acquisition_location=acquisition_location,
        content_digest=f"sha256:{issuing_gse}-source-digest",
        constraint_ids=("GSE-SPECIFIC-1001",),
    )
    repository = GseConstraintSourceRepositorySpy()

    registered_source = register_source(source_evidence, repository)

    assert registered_source.gse_classification == classification
    assert registered_source.issuing_authorities == frozenset({issuing_gse})
    assert registered_source.constraint_classifications == (
        ("GSE-SPECIFIC-1001", classification),
    )
    assert repository.saved_sources == [registered_source]
