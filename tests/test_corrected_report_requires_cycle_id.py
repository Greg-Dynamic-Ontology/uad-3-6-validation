"""Acceptance test for IT-25R3S3 correction cycle identification."""

from __future__ import annotations

from dataclasses import dataclass, field
from importlib import import_module
from typing import Any

import pytest


VALIDATION_CYCLES_MODULE = "app.services.validation_cycles"


@dataclass(frozen=True)
class CorrectedUadReportArtifact:
    report_id: str
    content: bytes


@dataclass
class UnexpectedCallStub:
    calls: int = 0

    def __call__(self) -> object:
        self.calls += 1
        raise AssertionError(
            "IT-25R3S3 must reject a correction before doing cycle work."
        )


@dataclass
class CorrectionRepositorySpy:
    cycle_lookups: list[object] = field(default_factory=list)
    saved_submissions: list[object] = field(default_factory=list)

    def get_by_id(self, validation_cycle_id: object) -> object:
        self.cycle_lookups.append(validation_cycle_id)
        raise AssertionError(
            "IT-25R3S3 must not guess or look up an unidentified cycle."
        )

    def save_submission(self, submission: object) -> None:
        self.saved_submissions.append(submission)


@dataclass
class ArtifactRetentionSpy:
    calls: list[tuple[object, str]] = field(default_factory=list)

    def retain(self, artifact: object, integrity_digest: str) -> str:
        self.calls.append((artifact, integrity_digest))
        raise AssertionError(
            "IT-25R3S3 must not retain an unassociated correction."
        )


def _required_cycle_id_contract() -> tuple[Any, type[Exception]]:
    """Load the missing-cycle-ID contract required by IT-25R3S3."""

    module = import_module(VALIDATION_CYCLES_MODULE)
    accept_correction = getattr(
        module,
        "accept_corrected_report_submission",
        None,
    )
    missing_cycle_id = getattr(
        module,
        "MissingValidationCycleIdentifierError",
        None,
    )
    assert callable(accept_correction)
    assert (
        isinstance(missing_cycle_id, type)
        and issubclass(missing_cycle_id, Exception)
    ), "IT-25R3S3 requires MissingValidationCycleIdentifierError."
    return accept_correction, missing_cycle_id


def test_it_25_r3_s3_requires_cycle_id_for_corrected_submission() -> None:
    """Reject an unidentified correction without guessing or attaching it."""

    accept_correction, missing_cycle_id = _required_cycle_id_contract()
    repository = CorrectionRepositorySpy()
    id_factory = UnexpectedCallStub()
    clock = UnexpectedCallStub()
    retention = ArtifactRetentionSpy()

    with pytest.raises(
        missing_cycle_id,
        match="validation cycle identifier",
    ):
        accept_correction(
            validation_cycle_id=None,
            corrected_report_artifact=CorrectedUadReportArtifact(
                report_id="uad-report-1",
                content=b"<UAD_REPORT revision='unidentified-correction'/>",
            ),
            submission_id_factory=id_factory,
            clock=clock,
            artifact_retention=retention,
            repository=repository,
        )

    assert repository.cycle_lookups == []
    assert repository.saved_submissions == []
    assert id_factory.calls == 0
    assert clock.calls == 0
    assert retention.calls == []
