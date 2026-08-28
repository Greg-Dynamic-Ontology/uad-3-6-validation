"""Acceptance test for IT-25R7S2 stale completion events."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from importlib import import_module
from typing import Any


VALIDATION_CYCLES_MODULE = "app.services.validation_cycles"


@dataclass(frozen=True)
class CurrentValidationCycle:
    validation_cycle_id: str
    state: str
    current_validation_submission_sequence: int
    current_validation_result_id: str


@dataclass(frozen=True)
class DelayedValidationCompletionEvent:
    completion_event_id: str
    validation_cycle_id: str
    validation_attempt_id: str
    validation_submission_id: str
    validation_submission_sequence: int
    validation_result_id: str
    resulting_cycle_state: str
    completed_at: datetime


@dataclass
class ValidationCompletionRepositorySpy:
    validation_cycle: CurrentValidationCycle
    duplicate_checks: list[str] = field(default_factory=list)
    cycle_lookups: list[str] = field(default_factory=list)
    saved_cycles: list[object] = field(default_factory=list)
    appended_results: list[tuple[str, str]] = field(default_factory=list)
    marked_event_ids: list[str] = field(default_factory=list)

    def has_applied_completion_event(self, completion_event_id: str) -> bool:
        self.duplicate_checks.append(completion_event_id)
        return False

    def get_by_id(self, validation_cycle_id: str) -> CurrentValidationCycle:
        self.cycle_lookups.append(validation_cycle_id)
        return self.validation_cycle

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


def _stale_completion_contract() -> tuple[Any, Any]:
    """Load the ordered completion contract required by IT-25R7S2."""

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
    assert callable(apply_completion)
    assert disposition is not None and hasattr(
        disposition,
        "STALE_IGNORED",
    ), (
        "IT-25R7S2 requires "
        "ValidationCompletionEventDisposition.STALE_IGNORED."
    )
    return apply_completion, disposition


def test_it_25_r7_s2_prevents_stale_result_from_changing_cycle() -> None:
    """Audit an older result without changing the newer current state."""

    apply_completion, disposition = _stale_completion_contract()
    validation_cycle_id = "6ad8df4d-df4a-4a2f-925e-2f57df436c92"
    cycle = CurrentValidationCycle(
        validation_cycle_id=validation_cycle_id,
        state="open",
        current_validation_submission_sequence=2,
        current_validation_result_id="validation-result-current-2",
    )
    original_cycle = cycle
    event = DelayedValidationCompletionEvent(
        completion_event_id="validation-completion-event-delayed-1",
        validation_cycle_id=validation_cycle_id,
        validation_attempt_id="validation-attempt-delayed-1",
        validation_submission_id="validation-submission-delayed-1",
        validation_submission_sequence=1,
        validation_result_id="validation-result-delayed-1",
        resulting_cycle_state="passed-and-closed",
        completed_at=datetime(2026, 8, 28, 8, 30, tzinfo=timezone.utc),
    )
    repository = ValidationCompletionRepositorySpy(cycle)
    credit_events = CreditLifecycleEventPublisherSpy()
    audit = CompletionEventAuditSpy()

    result = apply_completion(
        completion_event=event,
        repository=repository,
        credit_event_publisher=credit_events,
        audit=audit,
    )

    assert result is disposition.STALE_IGNORED
    assert repository.duplicate_checks == [event.completion_event_id]
    assert repository.cycle_lookups == [validation_cycle_id]
    assert repository.validation_cycle == original_cycle
    assert repository.validation_cycle.state == "open"
    assert repository.validation_cycle.current_validation_result_id == (
        "validation-result-current-2"
    )
    assert repository.saved_cycles == []
    assert repository.appended_results == []
    assert repository.marked_event_ids == [event.completion_event_id]
    assert credit_events.published_events == []
    assert audit.events == [
        {
            "event_type": "stale_validation_completion_event_ignored",
            "completion_event_id": event.completion_event_id,
            "validation_cycle_id": event.validation_cycle_id,
            "validation_attempt_id": event.validation_attempt_id,
            "validation_submission_id": event.validation_submission_id,
            "validation_result_id": event.validation_result_id,
        }
    ]
