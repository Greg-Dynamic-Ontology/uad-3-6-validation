"""Acceptance test for IT-30R2S2 distinct versioned GSE releases."""

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
    constraint_definitions: tuple[tuple[str, str], ...]


@dataclass
class VersionedGseConstraintSetRepositorySpy:
    saved_constraint_sets: list[object] = field(default_factory=list)

    def save(self, constraint_set: object) -> None:
        self.saved_constraint_sets.append(constraint_set)


def _versioned_release_registration_contract() -> Any:
    """Load versioned release registration required by IT-30R2S2."""

    module = import_module(GSE_CONSTRAINT_SOURCES_MODULE)
    register_releases = getattr(
        module,
        "register_versioned_gse_constraint_sets",
        None,
    )
    assert callable(register_releases), (
        "IT-30R2S2 requires register_versioned_gse_constraint_sets("
        "release_evidence, repository)."
    )
    return register_releases


def test_it_30_r2_s2_keeps_different_releases_distinct_when_ids_repeat() -> None:
    """Retain each release's own definition without rewriting the other."""

    register_releases = _versioned_release_registration_contract()
    joint_issuers = frozenset({"fannie_mae", "freddie_mac"})
    constraint_id = "UAD1001"
    release_1_4 = AuthoritativeGseConstraintReleaseEvidence(
        source_document_name="UAD Compliance Rules - URAR",
        source_version="1.4",
        issuing_authorities=joint_issuers,
        acquisition_location=(
            "specs/FannieMae/releases/1.4/appendix-h-1.xlsx"
        ),
        content_digest="sha256:joint-rules-1-4",
        constraint_ids=(constraint_id,),
        constraint_definitions=(
            (constraint_id, "release 1.4 source definition"),
        ),
    )
    release_1_5 = AuthoritativeGseConstraintReleaseEvidence(
        source_document_name="UAD Compliance Rules - URAR",
        source_version="1.5",
        issuing_authorities=joint_issuers,
        acquisition_location=(
            "specs/FannieMae/releases/1.5/appendix-h-1.xlsx"
        ),
        content_digest="sha256:joint-rules-1-5",
        constraint_ids=(constraint_id,),
        constraint_definitions=(
            (constraint_id, "release 1.5 source definition"),
        ),
    )
    repository = VersionedGseConstraintSetRepositorySpy()

    registered_sets = register_releases(
        (release_1_4, release_1_5),
        repository,
    )

    assert len(registered_sets) == 2
    first_release, second_release = registered_sets
    assert first_release.source_version == "1.4"
    assert first_release.content_digest == "sha256:joint-rules-1-4"
    assert first_release.constraint_definitions == (
        (constraint_id, "release 1.4 source definition"),
    )
    assert second_release.source_version == "1.5"
    assert second_release.content_digest == "sha256:joint-rules-1-5"
    assert second_release.constraint_definitions == (
        (constraint_id, "release 1.5 source definition"),
    )
    assert first_release.canonical_constraint_ids == (constraint_id,)
    assert second_release.canonical_constraint_ids == (constraint_id,)
    assert first_release is not second_release
    assert repository.saved_constraint_sets == [
        first_release,
        second_release,
    ]
