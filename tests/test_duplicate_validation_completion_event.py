"""Acceptance test for IT-25R7S2 duplicate completion events."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from importlib import import_module
from typing import Any


VALIDATION_CYCLES_MODULE = "app.services.validation_cycles"


@dataclass(frozen=True)
class ValidationCompletionEvent:
    completion_event_id: str
    validation_cycle_id: str
    validation_attempt_id: str
    validation_submission_id: str
    validation_result_id: str
    completed_at: datetime


@dataclass
class ValidationCompletionRepositorySpy:
    applied_event_ids: set[str]
    duplicate_checks: list[str] = field(default_factory=list)
    cycle_lookups: list[str] = field(default_factory=list)
    saved_cycles: list[object] = field(default_factory=list)
    appended_results: list[tuple[str, str]] = field(default_factory=list)
    marked_event_ids: list[str] = field(default_factory=list)

    def has_applied_completion_event(self, completion_event_id: str) -> bool:
        self.duplicate_checks.append(completion_event_id)
        return completion_event_id in self.applied_event_ids

    def get_by_id(self, validation_cycle_id: str) -> object:
        self.cycle_lookups.append(validation_cycle_id)
        raise AssertionError(
            "IT-25R7S2 must stop before loading a cycle for a duplicate event."
        )

    def save(self, validation_cycle: object) -> None:
        self.saved_cycles.append(validation_cycle)

    def append_result_history(
        self,
        validation_cycle_id: str,
        validation_result_id: str,
    ) -> None:
        self.appended_results.append(
            (validation_cycle_id, validation_result_id)
        )

    def mark_completion_event_applied(self, completion_event_id: str) -> None:
        self.marked_event_ids.append(completion_event_id)


@dataclass
class CreditLifecycleEventPublisherSpy:
    published_events: list[object] = field(default_factory=list)

    def publish(self, lifecycle_event: object) -> None:
        self.published_events.append(lifecycle_event)


@dataclass
class CompletionEventAuditSpy:
    events: list[dict[str, str]] = field(default_factory=list)

    def record(self, **event: str) -> None:
        self.events.append(event)


def _completion_event_contract() -> tuple[Any, Any]:
    """Load the exactly-once completion contract required by IT-25R7S1."""

    module = import_module(VALIDATION_CYCLES_MODULE)
    apply_completion = getattr(
        module,
        "apply_validation_completion_event",
        None,
    )
    disposition = getattr(
        module,
        "ValidationCompletionEventDisposition",
        None,
    )
    assert callable(apply_completion), (
        "IT-25R7S2 requires apply_validation_completion_event("
        "completion_event, repository, credit_event_publisher, audit)."
    )
    assert disposition is not None and hasattr(
        disposition,
        "DUPLICATE_IGNORED",
    ), (
        "IT-25R7S2 requires "
        "ValidationCompletionEventDisposition.DUPLICATE_IGNORED."
    )
    return apply_completion, disposition


def test_it_25_r7_s1_ignores_duplicate_validation_completion_event() -> None:
    """Audit a duplicate without repeating any previously applied effect."""

    apply_completion, disposition = _completion_event_contract()
    event = ValidationCompletionEvent(
        completion_event_id="validation-completion-event-1",
        validation_cycle_id="6ad8df4d-df4a-4a2f-925e-2f57df436c92",
        validation_attempt_id="validation-attempt-1",
        validation_submission_id="66a29861-f6d6-4572-91de-ce32d28a8421",
        validation_result_id="26b2f152-8176-48cf-b397-8ec662a528e3",
        completed_at=datetime(2026, 8, 28, 9, 0, tzinfo=timezone.utc),
    )
    repository = ValidationCompletionRepositorySpy(
        applied_event_ids={event.completion_event_id}
    )
    credit_events = CreditLifecycleEventPublisherSpy()
    audit = CompletionEventAuditSpy()

    result = apply_completion(
        completion_event=event,
        repository=repository,
        credit_event_publisher=credit_events,
        audit=audit,
    )

    assert result is disposition.DUPLICATE_IGNORED
    assert repository.duplicate_checks == [event.completion_event_id]
    assert repository.cycle_lookups == []
    assert repository.saved_cycles == []
    assert repository.appended_results == []
    assert repository.marked_event_ids == []
    assert credit_events.published_events == []
    assert audit.events == [
        {
            "event_type": "duplicate_validation_completion_event_ignored",
            "completion_event_id": event.completion_event_id,
            "validation_cycle_id": event.validation_cycle_id,
            "validation_attempt_id": event.validation_attempt_id,
            "validation_submission_id": event.validation_submission_id,
            "validation_result_id": event.validation_result_id,
        }
    ]
