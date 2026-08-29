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


class VersionedGseConstraintReleaseEvidence(
    AuthoritativeGseConstraintSourceEvidence,
    Protocol,
):
    constraint_definitions: tuple[tuple[str, str], ...]


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


class ClassifiedGseConstraintGovernanceRecord(Protocol):
    canonical_constraint_id: str
    gse_classification: str
    issuing_authorities: frozenset[str]
    source_document_name: str
    source_version: str
    content_digest: str
    source_sheet: str
    source_row: int


GovernanceRecord = TypeVar(
    "GovernanceRecord",
    bound=ClassifiedGseConstraintGovernanceRecord,
)


class GseConstraintGovernanceRepository(Protocol[GovernanceRecord]):
    def get_governance_record(
        self,
        canonical_constraint_id: str,
        source_version: str,
    ) -> GovernanceRecord | None: ...


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


@dataclass(frozen=True)
class RegisteredCanonicalGseConstraintSet:
    """One canonical release with all authoritative acquisition provenance."""

    source_document_name: str
    source_version: str
    issuing_authorities: frozenset[str]
    content_digest: str
    gse_classification: str
    canonical_constraint_ids: tuple[str, ...]
    acquisition_locations: tuple[str, ...]
    constraint_definitions: tuple[tuple[str, str], ...] = ()


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


def register_canonical_gse_constraint_set(
    source_evidence: tuple[AuthoritativeGseConstraintSourceEvidence, ...],
    repository: GseConstraintSourceRepository,
) -> RegisteredCanonicalGseConstraintSet:
    """Register identical authoritative copies as one shared GSE release."""

    if not source_evidence:
        raise ValueError("At least one authoritative source copy is required.")
    authoritative_evidence = (
        discover_authoritative_gse_constraint_sources(source_evidence)
    )
    if len(authoritative_evidence) != len(source_evidence):
        raise ValueError(
            "Every source copy must come from an authoritative GSE root."
        )

    signatures = {
        (
            evidence.source_document_name,
            evidence.source_version,
            evidence.issuing_authorities,
            evidence.content_digest,
            evidence.constraint_ids,
        )
        for evidence in authoritative_evidence
    }
    if len(signatures) != 1:
        raise ValueError(
            "Canonical copies must describe the same governed release."
        )

    first = authoritative_evidence[0]
    joint_issuers = frozenset({"fannie_mae", "freddie_mac"})
    if first.issuing_authorities != joint_issuers:
        raise ValueError(
            "A canonical joint release requires both GSEs as issuers."
        )

    registered_set = RegisteredCanonicalGseConstraintSet(
        source_document_name=first.source_document_name,
        source_version=first.source_version,
        issuing_authorities=first.issuing_authorities,
        content_digest=first.content_digest,
        gse_classification="shared",
        canonical_constraint_ids=tuple(dict.fromkeys(first.constraint_ids)),
        acquisition_locations=tuple(
            dict.fromkeys(
                evidence.acquisition_location
                for evidence in authoritative_evidence
            )
        ),
        constraint_definitions=getattr(
            first,
            "constraint_definitions",
            (),
        ),
    )
    repository.save(registered_set)
    return registered_set


def register_versioned_gse_constraint_sets(
    release_evidence: tuple[VersionedGseConstraintReleaseEvidence, ...],
    repository: GseConstraintSourceRepository,
) -> tuple[RegisteredCanonicalGseConstraintSet, ...]:
    """Register each governed release without rewriting another version."""

    registered_sets: list[RegisteredCanonicalGseConstraintSet] = []
    release_identities: set[tuple[str, str]] = set()
    for evidence in release_evidence:
        release_identity = (
            evidence.source_version,
            evidence.content_digest,
        )
        if release_identity in release_identities:
            raise ValueError(
                "Each versioned release identity may be registered once."
            )
        release_identities.add(release_identity)
        registered_sets.append(
            register_canonical_gse_constraint_set(
                (evidence,),
                repository,
            )
        )
    return tuple(registered_sets)


def get_classified_gse_constraint_governance_record(
    canonical_constraint_id: str,
    source_version: str,
    repository: GseConstraintGovernanceRepository[GovernanceRecord],
) -> GovernanceRecord:
    """Return one classified constraint's exact authoritative evidence."""

    governance_record = repository.get_governance_record(
        canonical_constraint_id,
        source_version,
    )
    if governance_record is None:
        raise LookupError(
            "No governance record exists for the requested constraint "
            "and source version."
        )
    if governance_record.canonical_constraint_id != canonical_constraint_id:
        raise ValueError("The repository returned another constraint.")
    if governance_record.source_version != source_version:
        raise ValueError("The repository returned another source version.")
    if (
        not governance_record.gse_classification
        or not governance_record.issuing_authorities
        or not governance_record.source_document_name
        or not governance_record.content_digest
        or not governance_record.source_sheet
        or governance_record.source_row < 1
    ):
        raise ValueError(
            "The classified constraint governance record is incomplete."
        )
    return governance_record


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
