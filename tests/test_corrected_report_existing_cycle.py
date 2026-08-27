"""Acceptance test for IT-25R3S2 corrected report submission."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from importlib import import_module
from typing import Any


VALIDATION_CYCLES_MODULE = "app.services.validation_cycles"


@dataclass(frozen=True)
class OpenValidationCycle:
    validation_cycle_id: str
    customer_account_id: str
    report_id: str
    state: str
    validation_submission_ids: tuple[str, ...]
    validation_result_ids: tuple[str, ...]


@dataclass(frozen=True)
class CorrectedUadReportArtifact:
    report_id: str
    content: bytes


@dataclass
class FixedFactory:
    value: str
    calls: int = 0

    def __call__(self) -> str:
        self.calls += 1
        return self.value


@dataclass
class FixedClock:
    value: datetime

    def __call__(self) -> datetime:
        return self.value


@dataclass
class ArtifactRetentionSpy:
    reference: str
    calls: list[tuple[object, str]] = field(default_factory=list)

    def retain(self, artifact: object, integrity_digest: str) -> str:
        self.calls.append((artifact, integrity_digest))
        return self.reference


@dataclass
class ValidationCycleRepositorySpy:
    validation_cycle: OpenValidationCycle
    cycle_lookups: list[str] = field(default_factory=list)
    saved_submissions: list[object] = field(default_factory=list)
    created_cycles: list[object] = field(default_factory=list)

    def get_by_id(self, validation_cycle_id: str) -> OpenValidationCycle:
        self.cycle_lookups.append(validation_cycle_id)
        return self.validation_cycle

    def save_submission(self, submission: object) -> None:
        self.saved_submissions.append(submission)

    def create_cycle(self, validation_cycle: object) -> None:
        self.created_cycles.append(validation_cycle)


def _corrected_submission_contract() -> Any:
    """Load the corrected-submission contract required by IT-25R3S2."""

    module = import_module(VALIDATION_CYCLES_MODULE)
    accept_correction = getattr(
        module,
        "accept_corrected_report_submission",
        None,
    )
    assert callable(accept_correction), (
        "IT-25R3S2 requires accept_corrected_report_submission("
        "validation_cycle_id, corrected_report_artifact, "
        "submission_id_factory, clock, artifact_retention, repository)."
    )
    return accept_correction


def test_it_25_r3_s2_accepts_correction_into_existing_open_cycle() -> None:
    """Create a new submission while preserving the existing cycle history."""

    accept_correction = _corrected_submission_contract()
    validation_cycle_id = "6ad8df4d-df4a-4a2f-925e-2f57df436c92"
    prior_submission_id = "66a29861-f6d6-4572-91de-ce32d28a8421"
    corrected_submission_id = "c4a41d23-3369-46d6-a5c1-ae580ee62281"
    cycle = OpenValidationCycle(
        validation_cycle_id=validation_cycle_id,
        customer_account_id="customer-account-1",
        report_id="uad-report-1",
        state="open",
        validation_submission_ids=(prior_submission_id,),
        validation_result_ids=("validation-result-with-findings-1",),
    )
    original_cycle = cycle
    corrected_artifact = CorrectedUadReportArtifact(
        report_id=cycle.report_id,
        content=b"<UAD_REPORT revision='corrected'/>",
    )
    id_factory = FixedFactory(corrected_submission_id)
    repository = ValidationCycleRepositorySpy(cycle)

    submission = accept_correction(
        validation_cycle_id=validation_cycle_id,
        corrected_report_artifact=corrected_artifact,
        submission_id_factory=id_factory,
        clock=FixedClock(
            datetime(2026, 8, 27, 16, 30, tzinfo=timezone.utc)
        ),
        artifact_retention=ArtifactRetentionSpy(
            "artifact://submission/corrected-1"
        ),
        repository=repository,
    )

    assert repository.cycle_lookups == [validation_cycle_id]
    assert submission.validation_cycle_id == validation_cycle_id
    assert submission.validation_submission_id == corrected_submission_id
    assert submission.validation_submission_id != prior_submission_id
    assert id_factory.calls == 1
    assert repository.saved_submissions == [submission]
    assert repository.created_cycles == []
    assert repository.validation_cycle == original_cycle
    assert repository.validation_cycle.state == "open"
    assert repository.validation_cycle.validation_submission_ids == (
        prior_submission_id,
    )
    assert repository.validation_cycle.validation_result_ids == (
        "validation-result-with-findings-1",
    )
