"""Acceptance test for IT-30R1S1 jointly issued GSE source evidence."""

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


def _joint_source_registration_contract() -> Any:
    """Load the governed source registration required by IT-30R1S1."""

    try:
        module = import_module(GSE_CONSTRAINT_SOURCES_MODULE)
    except ModuleNotFoundError as error:
        if error.name != GSE_CONSTRAINT_SOURCES_MODULE:
            raise
        pytest.fail(
            "IT-30R1S1 requires app.services.gse_constraint_sources "
            "before jointly issued source evidence can become green.",
            pytrace=False,
        )

    register_source = getattr(
        module,
        "register_authoritative_gse_constraint_source",
        None,
    )
    assert callable(register_source), (
        "IT-30R1S1 requires "
        "register_authoritative_gse_constraint_source("
        "source_evidence, repository)."
    )
    return register_source


def test_it_30_r1_s1_recognizes_a_jointly_issued_gse_constraint_source() -> None:
    """Use issuer evidence, not the acquisition folder, to classify the source."""

    register_source = _joint_source_registration_contract()
    source_evidence = AuthoritativeGseConstraintSourceEvidence(
        source_document_name=(
            "UAD Compliance Rules - Uniform Residential Appraisal Report"
        ),
        source_version="1.5",
        issuing_authorities=frozenset({"fannie_mae", "freddie_mac"}),
        acquisition_location=(
            "specs/FannieMae/appendix-h-1-uad-compliance-rules-urar.xlsx"
        ),
        content_digest=(
            "df94cfb44b7460a619786a2e4f8c68ef"
            "472b167926ed0a3377ff6fb43ac283e8"
        ),
        constraint_ids=("UAD1001", "UAD1002"),
    )
    repository = GseConstraintSourceRepositorySpy()

    registered_source = register_source(source_evidence, repository)

    assert registered_source.gse_classification == "shared"
    assert registered_source.issuing_authorities == frozenset(
        {"fannie_mae", "freddie_mac"}
    )
    assert registered_source.acquisition_location == (
        source_evidence.acquisition_location
    )
    assert registered_source.constraint_classifications == (
        ("UAD1001", "shared"),
        ("UAD1002", "shared"),
    )
    assert repository.saved_sources == [registered_source]
