"""Acceptance test for IT-30R2S1 canonical joint GSE releases."""

from __future__ import annotations

from dataclasses import dataclass, field
from importlib import import_module
from typing import Any


GSE_CONSTRAINT_SOURCES_MODULE = "app.services.gse_constraint_sources"


@dataclass(frozen=True)
class AuthoritativeGseConstraintReleaseEvidence:
    source_document_name: str
    source_version: str
    issuing_authorities: frozenset[str]
    acquisition_location: str
    content_digest: str
    constraint_ids: tuple[str, ...]


@dataclass
class CanonicalGseConstraintSetRepositorySpy:
    saved_constraint_sets: list[object] = field(default_factory=list)

    def save(self, constraint_set: object) -> None:
        self.saved_constraint_sets.append(constraint_set)


def _canonical_joint_release_contract() -> Any:
    """Load canonical joint-release registration required by IT-30R2S1."""

    module = import_module(GSE_CONSTRAINT_SOURCES_MODULE)
    register_constraint_set = getattr(
        module,
        "register_canonical_gse_constraint_set",
        None,
    )
    assert callable(register_constraint_set), (
        "IT-30R2S1 requires register_canonical_gse_constraint_set("
        "source_evidence, repository)."
    )
    return register_constraint_set


def test_it_30_r2_s1_treats_identical_joint_release_copies_as_one_constraint_set() -> None:
    """Deduplicate the release while preserving both acquisition locations."""

    register_constraint_set = _canonical_joint_release_contract()
    joint_issuers = frozenset({"fannie_mae", "freddie_mac"})
    document_name = "UAD Compliance Rules - URAR"
    version = "1.5"
    digest = "sha256:joint-uad-compliance-rules-v1-5"
    constraint_ids = ("UAD1001", "UAD1002")
    fannie_copy = AuthoritativeGseConstraintReleaseEvidence(
        source_document_name=document_name,
        source_version=version,
        issuing_authorities=joint_issuers,
        acquisition_location=(
            "specs/FannieMae/appendix-h-1-uad-compliance-rules-urar.xlsx"
        ),
        content_digest=digest,
        constraint_ids=constraint_ids,
    )
    freddie_copy = AuthoritativeGseConstraintReleaseEvidence(
        source_document_name=document_name,
        source_version=version,
        issuing_authorities=joint_issuers,
        acquisition_location=(
            "specs/FreddieMac/appendix-h-1-uad-compliance-rules-urar.xlsx"
        ),
        content_digest=digest,
        constraint_ids=constraint_ids,
    )
    repository = CanonicalGseConstraintSetRepositorySpy()

    registered_set = register_constraint_set(
        (fannie_copy, freddie_copy),
        repository,
    )

    assert registered_set.gse_classification == "shared"
    assert registered_set.source_document_name == document_name
    assert registered_set.source_version == version
    assert registered_set.content_digest == digest
    assert registered_set.canonical_constraint_ids == constraint_ids
    assert len(set(registered_set.canonical_constraint_ids)) == 2
    assert registered_set.acquisition_locations == (
        fannie_copy.acquisition_location,
        freddie_copy.acquisition_location,
    )
    assert repository.saved_constraint_sets == [registered_set]
