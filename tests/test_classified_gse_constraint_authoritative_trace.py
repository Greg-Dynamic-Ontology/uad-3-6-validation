"""Acceptance test for IT-30R2S3 authoritative constraint traceability."""

from __future__ import annotations

from dataclasses import dataclass, field
from importlib import import_module
from typing import Any


GSE_CONSTRAINT_SOURCES_MODULE = "app.services.gse_constraint_sources"


@dataclass(frozen=True)
class ClassifiedGseConstraintGovernanceRecord:
    canonical_constraint_id: str
    gse_classification: str
    issuing_authorities: frozenset[str]
    source_document_name: str
    source_version: str
    content_digest: str
    source_sheet: str
    source_row: int


@dataclass
class GseConstraintGovernanceRepositorySpy:
    governance_record: ClassifiedGseConstraintGovernanceRecord
    lookup_calls: list[tuple[str, str]] = field(default_factory=list)

    def get_governance_record(
        self,
        canonical_constraint_id: str,
        source_version: str,
    ) -> ClassifiedGseConstraintGovernanceRecord | None:
        self.lookup_calls.append(
            (canonical_constraint_id, source_version)
        )
        if (
            self.governance_record.canonical_constraint_id
            == canonical_constraint_id
            and self.governance_record.source_version == source_version
        ):
            return self.governance_record
        return None


def _constraint_governance_trace_contract() -> Any:
    """Load classified-constraint lookup required by IT-30R2S3."""

    module = import_module(GSE_CONSTRAINT_SOURCES_MODULE)
    get_governance_record = getattr(
        module,
        "get_classified_gse_constraint_governance_record",
        None,
    )
    assert callable(get_governance_record), (
        "IT-30R2S3 requires "
        "get_classified_gse_constraint_governance_record("
        "canonical_constraint_id, source_version, repository)."
    )
    return get_governance_record


def test_it_30_r2_s3_traces_a_classified_constraint_to_authoritative_evidence() -> None:
    """Return the exact authority and source location for one release."""

    get_governance_record = _constraint_governance_trace_contract()
    expected_record = ClassifiedGseConstraintGovernanceRecord(
        canonical_constraint_id="UAD1001",
        gse_classification="shared",
        issuing_authorities=frozenset(
            {"fannie_mae", "freddie_mac"}
        ),
        source_document_name="UAD Compliance Rules - URAR",
        source_version="1.5",
        content_digest="sha256:joint-uad-compliance-rules-v1-5",
        source_sheet="UAD Compliance Rules v1.5",
        source_row=2,
    )
    repository = GseConstraintGovernanceRepositorySpy(expected_record)

    governance_record = get_governance_record(
        "UAD1001",
        "1.5",
        repository,
    )

    assert governance_record is expected_record
    assert governance_record.canonical_constraint_id == "UAD1001"
    assert governance_record.gse_classification == "shared"
    assert governance_record.issuing_authorities == frozenset(
        {"fannie_mae", "freddie_mac"}
    )
    assert governance_record.source_document_name == (
        "UAD Compliance Rules - URAR"
    )
    assert governance_record.source_version == "1.5"
    assert governance_record.content_digest == (
        "sha256:joint-uad-compliance-rules-v1-5"
    )
    assert governance_record.source_sheet == "UAD Compliance Rules v1.5"
    assert governance_record.source_row == 2
    assert repository.lookup_calls == [("UAD1001", "1.5")]
