"""Govern authoritative source evidence for GSE constraints."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, TypeVar


class AmbiguousGseAuthorityError(ValueError):
    """Raised when governed evidence cannot establish GSE authority."""


class AuthoritativeGseConstraintSourceEvidence(Protocol):
    source_document_name: str
    source_version: str
    issuing_authorities: frozenset[str]
    acquisition_location: str
    content_digest: str
    constraint_ids: tuple[str, ...]


class GseConstraintSourceRepository(Protocol):
    def save(self, registered_source: object) -> None: ...


class GseAuthorityGovernanceReview(Protocol):
    def record(self, **event: object) -> None: ...


class GseConstraintSourceCandidate(Protocol):
    acquisition_location: str


SourceCandidate = TypeVar(
    "SourceCandidate",
    bound=GseConstraintSourceCandidate,
)


@dataclass(frozen=True)
class RegisteredGseConstraintSource:
    """One governed source classified from its explicit issuer evidence."""

    source_document_name: str
    source_version: str
    issuing_authorities: frozenset[str]
    acquisition_location: str
    content_digest: str
    gse_classification: str
    constraint_classifications: tuple[tuple[str, str], ...]


def discover_authoritative_gse_constraint_sources(
    candidate_sources: tuple[SourceCandidate, ...],
) -> tuple[SourceCandidate, ...]:
    """Return only candidates acquired from governed GSE source roots."""

    authoritative_roots = (
        "/specs/fanniemae/",
        "/specs/freddiemac/",
    )
    return tuple(
        candidate
        for candidate in candidate_sources
        if any(
            root
            in (
                "/"
                + candidate.acquisition_location
                .replace("\\", "/")
                .strip("/")
                .casefold()
                + "/"
            )
            for root in authoritative_roots
        )
    )


def register_authoritative_gse_constraint_source(
    source_evidence: AuthoritativeGseConstraintSourceEvidence,
    repository: GseConstraintSourceRepository,
    governance_review: GseAuthorityGovernanceReview | None = None,
) -> RegisteredGseConstraintSource:
    """Classify a source from explicit issuer evidence, never its folder."""

    classifications_by_issuers = {
        frozenset({"fannie_mae", "freddie_mac"}): "shared",
        frozenset({"fannie_mae"}): "fannie_mae_only",
        frozenset({"freddie_mac"}): "freddie_mac_only",
    }
    try:
        classification = classifications_by_issuers[
            source_evidence.issuing_authorities
        ]
    except KeyError as error:
        if governance_review is not None:
            governance_review.record(
                event_type="ambiguous-gse-authority",
                source_document_name=source_evidence.source_document_name,
                source_version=source_evidence.source_version,
                acquisition_location=source_evidence.acquisition_location,
                content_digest=source_evidence.content_digest,
            )
        raise AmbiguousGseAuthorityError(
            "Authoritative GSE source registration requires explicit "
            "evidence of Fannie Mae, Freddie Mac, or both as issuers."
        ) from error
    if not source_evidence.source_document_name.strip():
        raise ValueError("An authoritative source document name is required.")
    if not source_evidence.source_version.strip():
        raise ValueError("An authoritative source version is required.")
    if not source_evidence.content_digest.strip():
        raise ValueError("An authoritative source content digest is required.")

    registered_source = RegisteredGseConstraintSource(
        source_document_name=source_evidence.source_document_name,
        source_version=source_evidence.source_version,
        issuing_authorities=source_evidence.issuing_authorities,
        acquisition_location=source_evidence.acquisition_location,
        content_digest=source_evidence.content_digest,
        gse_classification=classification,
        constraint_classifications=tuple(
            (constraint_id, classification)
            for constraint_id in source_evidence.constraint_ids
        ),
    )
    repository.save(registered_source)
    return registered_source
