"""Acceptance test for IT-30R1S3 experimental-source exclusion."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from typing import Any


GSE_CONSTRAINT_SOURCES_MODULE = "app.services.gse_constraint_sources"


@dataclass(frozen=True)
class GseConstraintSourceCandidate:
    source_document_name: str
    source_version: str
    issuing_authorities: frozenset[str]
    acquisition_location: str
    content_digest: str


def _authoritative_source_discovery_contract() -> Any:
    """Load authoritative discovery required by IT-30R1S3."""

    module = import_module(GSE_CONSTRAINT_SOURCES_MODULE)
    discover_sources = getattr(
        module,
        "discover_authoritative_gse_constraint_sources",
        None,
    )
    assert callable(discover_sources), (
        "IT-30R1S3 requires "
        "discover_authoritative_gse_constraint_sources("
        "candidate_sources)."
    )
    return discover_sources


def test_it_30_r1_s3_excludes_experimental_material_from_authoritative_ingestion() -> None:
    """Do not let an experimental copy establish authority or active version."""

    discover_sources = _authoritative_source_discovery_contract()
    joint_issuers = frozenset({"fannie_mae", "freddie_mac"})
    authoritative_digest = "sha256:authoritative-joint-release-1-5"
    fannie_acquisition = GseConstraintSourceCandidate(
        source_document_name="UAD Compliance Rules - URAR",
        source_version="1.5",
        issuing_authorities=joint_issuers,
        acquisition_location=(
            "specs/FannieMae/appendix-h-1-uad-compliance-rules-urar.xlsx"
        ),
        content_digest=authoritative_digest,
    )
    freddie_acquisition = GseConstraintSourceCandidate(
        source_document_name="UAD Compliance Rules - URAR",
        source_version="1.5",
        issuing_authorities=joint_issuers,
        acquisition_location=(
            "specs/FreddieMac/appendix-h-1-uad-compliance-rules-urar.xlsx"
        ),
        content_digest=authoritative_digest,
    )
    experimental_copy = GseConstraintSourceCandidate(
        source_document_name="Experimental UAD Compliance Rules",
        source_version="99.0",
        issuing_authorities=joint_issuers,
        acquisition_location=(
            "specs/UAD/Appendix H-1 UAD Compliance Rules - URAR.xlsm"
        ),
        content_digest="sha256:experimental-copy",
    )

    authoritative_sources = discover_sources(
        (fannie_acquisition, experimental_copy, freddie_acquisition)
    )

    assert authoritative_sources == (
        fannie_acquisition,
        freddie_acquisition,
    )
    assert experimental_copy not in authoritative_sources
    assert {source.source_version for source in authoritative_sources} == {
        "1.5"
    }
    assert all(
        not source.acquisition_location.replace("\\", "/").startswith(
            "specs/UAD/"
        )
        for source in authoritative_sources
    )
