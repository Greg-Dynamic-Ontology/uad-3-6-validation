"""Acceptance test for IT-25R8S1 append-only cycle history."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from importlib import import_module
from typing import Any


VALIDATION_CYCLES_MODULE = "app.services.validation_cycles"


@dataclass(frozen=True)
class ValidationCycleHistoryEvent:
    history_event_id: str
    validation_cycle_id: str
    event_type: str
    subject_id: str
    effective_at: datetime


@dataclass
class ValidationCycleHistoryRepositorySpy:
    events: list[ValidationCycleHistoryEvent] = field(default_factory=list)
    append_calls: list[ValidationCycleHistoryEvent] = field(default_factory=list)
    list_calls: list[str] = field(default_factory=list)
    replacement_calls: list[object] = field(default_factory=list)

    def append_event(self, event: ValidationCycleHistoryEvent) -> None:
        self.append_calls.append(event)
        self.events.append(event)

    def list_events(
        self,
        validation_cycle_id: str,
    ) -> tuple[ValidationCycleHistoryEvent, ...]:
        self.list_calls.append(validation_cycle_id)
        return tuple(
            event
            for event in self.events
            if event.validation_cycle_id == validation_cycle_id
        )

    def replace_events(self, events: object) -> None:
        self.replacement_calls.append(events)


def _append_only_history_contract() -> tuple[Any, Any]:
    """Load the append-only history contract required by IT-25R8S1."""

    module = import_module(VALIDATION_CYCLES_MODULE)
    append_event = getattr(
        module,
        "append_validation_cycle_history_event",
        None,
    )
    get_history = getattr(
        module,
        "get_validation_cycle_history",
        None,
    )
    assert callable(append_event), (
        "IT-25R8S1 requires append_validation_cycle_history_event("
        "validation_cycle_id, history_event, repository)."
    )
    assert callable(get_history), (
        "IT-25R8S1 requires get_validation_cycle_history("
        "validation_cycle_id, repository)."
    )
    return append_event, get_history


def test_it_25_r8_s1_preserves_append_only_cycle_history() -> None:
    """Retain every prior event when later cycle activity is appended."""

    append_event, get_history = _append_only_history_contract()
    validation_cycle_id = "6ad8df4d-df4a-4a2f-925e-2f57df436c92"
    initial_events = (
        ValidationCycleHistoryEvent(
            history_event_id="history-event-submission-1",
            validation_cycle_id=validation_cycle_id,
            event_type="validation-submission-accepted",
            subject_id="validation-submission-1",
            effective_at=datetime(2026, 8, 28, 9, 0, tzinfo=timezone.utc),
        ),
        ValidationCycleHistoryEvent(
            history_event_id="history-event-attempt-1",
            validation_cycle_id=validation_cycle_id,
            event_type="validation-attempt-started",
            subject_id="validation-attempt-1",
            effective_at=datetime(2026, 8, 28, 9, 1, tzinfo=timezone.utc),
        ),
        ValidationCycleHistoryEvent(
            history_event_id="history-event-result-1",
            validation_cycle_id=validation_cycle_id,
            event_type="validation-result-recorded",
            subject_id="validation-result-1",
            effective_at=datetime(2026, 8, 28, 9, 2, tzinfo=timezone.utc),
        ),
        ValidationCycleHistoryEvent(
            history_event_id="history-event-transition-1",
            validation_cycle_id=validation_cycle_id,
            event_type="validation-cycle-opened",
            subject_id=validation_cycle_id,
            effective_at=datetime(2026, 8, 28, 9, 3, tzinfo=timezone.utc),
        ),
    )
    later_event = ValidationCycleHistoryEvent(
        history_event_id="history-event-submission-2",
        validation_cycle_id=validation_cycle_id,
        event_type="validation-submission-accepted",
        subject_id="validation-submission-2",
        effective_at=datetime(2026, 8, 28, 10, 0, tzinfo=timezone.utc),
    )
    repository = ValidationCycleHistoryRepositorySpy()

    for event in initial_events:
        append_event(validation_cycle_id, event, repository)
    history_before_later_event = get_history(validation_cycle_id, repository)

    append_event(validation_cycle_id, later_event, repository)
    complete_history = get_history(validation_cycle_id, repository)

    assert history_before_later_event == initial_events
    assert complete_history == initial_events + (later_event,)
    assert complete_history[: len(initial_events)] == initial_events
    assert {event.event_type for event in complete_history} >= {
        "validation-submission-accepted",
        "validation-attempt-started",
        "validation-result-recorded",
        "validation-cycle-opened",
    }
    assert all(event.subject_id for event in complete_history)
    assert all(event.effective_at.tzinfo is not None for event in complete_history)
    assert repository.append_calls == [*initial_events, later_event]
    assert repository.list_calls == [validation_cycle_id, validation_cycle_id]
    assert repository.replacement_calls == []
