"""Acceptance test for IT-30R1S4 ambiguous GSE authority."""

from __future__ import annotations

from dataclasses import dataclass, field
from importlib import import_module
from typing import Any

import pytest


GSE_CONSTRAINT_SOURCES_MODULE = "app.services.gse_constraint_sources"


@dataclass(frozen=True)
class AmbiguousGseConstraintSourceEvidence:
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


@dataclass
class GovernanceReviewSpy:
    events: list[dict[str, object]] = field(default_factory=list)

    def record(self, **event: object) -> None:
        self.events.append(event)


def _ambiguous_authority_contract() -> tuple[Any, type[Exception]]:
    """Load the ambiguity rejection contract required by IT-30R1S4."""

    module = import_module(GSE_CONSTRAINT_SOURCES_MODULE)
    register_source = getattr(
        module,
        "register_authoritative_gse_constraint_source",
        None,
    )
    ambiguity_error = getattr(
        module,
        "AmbiguousGseAuthorityError",
        None,
    )
    assert callable(register_source), (
        "IT-30R1S4 requires "
        "register_authoritative_gse_constraint_source(...)."
    )
    assert isinstance(ambiguity_error, type) and issubclass(
        ambiguity_error,
        Exception,
    ), "IT-30R1S4 requires AmbiguousGseAuthorityError."
    return register_source, ambiguity_error


def test_it_30_r1_s4_refuses_to_guess_an_ambiguous_gse_authority() -> None:
    """Reject ambiguity and report it without inferring from the folder."""

    register_source, ambiguity_error = _ambiguous_authority_contract()
    source_evidence = AmbiguousGseConstraintSourceEvidence(
        source_document_name="Candidate appraisal constraints",
        source_version="1.0",
        issuing_authorities=frozenset(),
        acquisition_location="specs/FannieMae/candidate-constraints.xlsx",
        content_digest="sha256:ambiguous-authority",
        constraint_ids=("CANDIDATE-1001",),
    )
    repository = GseConstraintSourceRepositorySpy()
    governance_review = GovernanceReviewSpy()

    with pytest.raises(ambiguity_error):
        register_source(
            source_evidence,
            repository,
            governance_review=governance_review,
        )

    assert repository.saved_sources == []
    assert governance_review.events == [
        {
            "event_type": "ambiguous-gse-authority",
            "source_document_name": source_evidence.source_document_name,
            "source_version": source_evidence.source_version,
            "acquisition_location": source_evidence.acquisition_location,
            "content_digest": source_evidence.content_digest,
        }
    ]
