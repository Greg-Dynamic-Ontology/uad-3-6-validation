"""Acceptance test for IT-25R5S3 artifact-ingestion cancellation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from importlib import import_module
from typing import Any


VALIDATION_CYCLES_MODULE = "app.services.validation_cycles"


@dataclass
class ValidationCycleRepositorySpy:
    validation_cycle: object
    cycle_lookups: list[str] = field(default_factory=list)
    saved_cycles: list[object] = field(default_factory=list)
    history_events: list[tuple[str, object]] = field(default_factory=list)

    def get_by_id(self, validation_cycle_id: str) -> object:
        self.cycle_lookups.append(validation_cycle_id)
        return self.validation_cycle

    def save(self, validation_cycle: object) -> None:
        self.saved_cycles.append(validation_cycle)

    def append_history_event(
        self,
        validation_cycle_id: str,
        lifecycle_event: object,
    ) -> None:
        self.history_events.append((validation_cycle_id, lifecycle_event))


@dataclass
class CreditLifecycleEventPublisherSpy:
    published_events: list[object] = field(default_factory=list)

    def publish(self, lifecycle_event: object) -> None:
        self.published_events.append(lifecycle_event)


@dataclass
class FixedClock:
    value: datetime

    def __call__(self) -> datetime:
        return self.value


def _ingestion_failure_contract() -> tuple[Any, type[Any]]:
    """Load the ingestion-cancellation contract required by IT-25R5S3."""

    module = import_module(VALIDATION_CYCLES_MODULE)
    cancel_cycle = getattr(
        module,
        "cancel_pending_cycle_for_ingestion_failure",
        None,
    )
    pending_cycle = getattr(module, "PendingValidationCycle", None)
    assert callable(cancel_cycle), (
        "IT-25R5S3 requires "
        "cancel_pending_cycle_for_ingestion_failure("
        "validation_cycle_id, failure_reason, clock, repository, "
        "credit_event_publisher)."
    )
    assert isinstance(pending_cycle, type)
    return cancel_cycle, pending_cycle


def test_it_25_r5_s3_cancels_cycle_when_artifact_cannot_be_ingested() -> None:
    """Cancel without billing and retain the ingestion failure in history."""

    cancel_cycle, pending_cycle = _ingestion_failure_contract()
    validation_cycle_id = "6ad8df4d-df4a-4a2f-925e-2f57df436c92"
    failure_reason = "The uploaded artifact is not a readable UAD report."
    cancellation_time = datetime(2026, 8, 27, 18, 30, tzinfo=timezone.utc)
    cycle = pending_cycle(
        validation_cycle_id=validation_cycle_id,
        customer_account_id="customer-account-1",
        actor_id="human-user-validator",
        report_id="accepted-upload-1",
        state="pending",
        created_at=datetime(2026, 8, 27, 17, 30, tzinfo=timezone.utc),
    )
    original_cycle = cycle
    repository = ValidationCycleRepositorySpy(cycle)
    credit_events = CreditLifecycleEventPublisherSpy()

    cancelled_cycle = cancel_cycle(
        validation_cycle_id=validation_cycle_id,
        failure_reason=failure_reason,
        clock=FixedClock(cancellation_time),
        repository=repository,
        credit_event_publisher=credit_events,
    )

    assert original_cycle.state == "pending"
    assert cancelled_cycle.state == "cancelled"
    assert cancelled_cycle.current_validation_result_id is None
    assert cancelled_cycle.billable_validation_service_delivered is False
    assert repository.cycle_lookups == [validation_cycle_id]
    assert repository.saved_cycles == [cancelled_cycle]
    assert len(repository.history_events) == 1
    history_cycle_id, history_event = repository.history_events[0]
    assert history_cycle_id == validation_cycle_id
    assert history_event.failure_category == "artifact-ingestion-failure"
    assert history_event.failure_reason == failure_reason
    assert history_event.occurred_at == cancellation_time
    assert credit_events.published_events == [history_event]
    assert history_event.event_type == "validation_cycle_cancelled"
    assert history_event.previous_state == "pending"
    assert history_event.current_state == "cancelled"
    assert history_event.billable_validation_service_delivered is False
