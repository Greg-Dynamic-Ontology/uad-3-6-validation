"""Acceptance test for IT-25R3S1 validation-submission identity."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
from importlib import import_module
from typing import Any
from uuid import UUID


VALIDATION_CYCLES_MODULE = "app.services.validation_cycles"


@dataclass(frozen=True)
class UadReportArtifact:
    report_id: str
    content: bytes


@dataclass
class SequenceFactory:
    values: list[str]

    def __call__(self) -> str:
        return self.values.pop(0)


@dataclass
class SequenceClock:
    values: list[datetime]

    def __call__(self) -> datetime:
        return self.values.pop(0)


@dataclass
class ArtifactRetentionSpy:
    references: list[str]
    calls: list[tuple[object, str]] = field(default_factory=list)

    def retain(self, artifact: object, integrity_digest: str) -> str:
        self.calls.append((artifact, integrity_digest))
        return self.references.pop(0)


@dataclass
class ValidationSubmissionRepositorySpy:
    saved_submissions: list[object] = field(default_factory=list)

    def save_submission(self, submission: object) -> None:
        self.saved_submissions.append(submission)


def _submission_identity_contract() -> Any:
    """Load the accepted-submission contract required by IT-25R3S1."""

    module = import_module(VALIDATION_CYCLES_MODULE)
    accept_submission = getattr(
        module,
        "accept_report_submission",
        None,
    )
    assert callable(accept_submission), (
        "IT-25R3S1 requires accept_report_submission("
        "validation_cycle_id, report_artifact, submission_id_factory, "
        "clock, artifact_retention, repository)."
    )
    return accept_submission


def test_it_25_r3_s1_assigns_identity_to_every_accepted_submission() -> None:
    """Give each acceptance its own identity and traceable artifact record."""

    accept_submission = _submission_identity_contract()
    validation_cycle_id = "6ad8df4d-df4a-4a2f-925e-2f57df436c92"
    submission_ids = [
        "66a29861-f6d6-4572-91de-ce32d28a8421",
        "c4a41d23-3369-46d6-a5c1-ae580ee62281",
    ]
    accepted_times = [
        datetime(2026, 8, 27, 16, 0, tzinfo=timezone.utc),
        datetime(2026, 8, 27, 16, 5, tzinfo=timezone.utc),
    ]
    artifact = UadReportArtifact(
        report_id="uad-report-1",
        content=b"<UAD_REPORT id='uad-report-1'/>",
    )
    expected_digest = sha256(artifact.content).hexdigest()
    id_factory = SequenceFactory(submission_ids.copy())
    clock = SequenceClock(accepted_times.copy())
    retention = ArtifactRetentionSpy(
        references=["artifact://submission/1", "artifact://submission/2"]
    )
    repository = ValidationSubmissionRepositorySpy()

    submissions = [
        accept_submission(
            validation_cycle_id=validation_cycle_id,
            report_artifact=artifact,
            submission_id_factory=id_factory,
            clock=clock,
            artifact_retention=retention,
            repository=repository,
        )
        for _ in range(2)
    ]

    assert [submission.validation_submission_id for submission in submissions] == (
        submission_ids
    )
    distinct_submission_ids = {
        submission.validation_submission_id for submission in submissions
    }
    assert len(distinct_submission_ids) == 2
    assert all(
        UUID(submission.validation_submission_id)
        for submission in submissions
    )
    assert all(
        submission.validation_cycle_id == validation_cycle_id
        for submission in submissions
    )
    assert [submission.accepted_at for submission in submissions] == accepted_times
    assert all(
        submission.integrity_digest == expected_digest
        for submission in submissions
    )
    assert [submission.artifact_reference for submission in submissions] == [
        "artifact://submission/1",
        "artifact://submission/2",
    ]
    assert retention.calls == [
        (artifact, expected_digest),
        (artifact, expected_digest),
    ]
    assert repository.saved_submissions == submissions
