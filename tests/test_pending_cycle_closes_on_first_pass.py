"""Acceptance test for IT-25R5S2 pending-cycle passing outcome."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from importlib import import_module
from typing import Any


VALIDATION_CYCLES_MODULE = "app.services.validation_cycles"


@dataclass(frozen=True)
class PassingActionableValidationResult:
    validation_result_id: str
    validation_submission_id: str
    actionable: bool
    passed: bool
    findings: tuple[object, ...]


@dataclass
class ValidationCycleRepositorySpy:
    validation_cycle: object
    accepted_submission_ids: set[str]
    cycle_lookups: list[str] = field(default_factory=list)
    association_checks: list[tuple[str, str]] = field(default_factory=list)
    saved_cycles: list[object] = field(default_factory=list)

    def get_by_id(self, validation_cycle_id: str) -> object:
        self.cycle_lookups.append(validation_cycle_id)
        return self.validation_cycle

    def submission_belongs_to_cycle(
        self,
        validation_cycle_id: str,
        validation_submission_id: str,
    ) -> bool:
        self.association_checks.append(
            (validation_cycle_id, validation_submission_id)
        )
        return validation_submission_id in self.accepted_submission_ids

    def save(self, validation_cycle: object) -> None:
        self.saved_cycles.append(validation_cycle)


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


def _passing_first_result_contract() -> tuple[Any, type[Any]]:
    """Load the first-result lifecycle contract required by IT-25R5S2."""

    module = import_module(VALIDATION_CYCLES_MODULE)
    apply_result = getattr(
        module,
        "apply_first_actionable_validation_result",
        None,
    )
    pending_cycle = getattr(module, "PendingValidationCycle", None)
    assert callable(apply_result)
    assert isinstance(pending_cycle, type)
    return apply_result, pending_cycle


def test_it_25_r5_s2_closes_pending_cycle_when_first_result_passes() -> None:
    """Close the passing cycle and publish billable service delivery."""

    apply_result, pending_cycle = _passing_first_result_contract()
    validation_cycle_id = "6ad8df4d-df4a-4a2f-925e-2f57df436c92"
    validation_submission_id = "66a29861-f6d6-4572-91de-ce32d28a8421"
    validation_result_id = "26b2f152-8176-48cf-b397-8ec662a528e3"
    transition_time = datetime(2026, 8, 27, 18, 15, tzinfo=timezone.utc)
    cycle = pending_cycle(
        validation_cycle_id=validation_cycle_id,
        customer_account_id="customer-account-1",
        actor_id="human-user-validator",
        report_id="uad-report-1",
        state="pending",
        created_at=datetime(2026, 8, 27, 17, 30, tzinfo=timezone.utc),
    )
    original_cycle = cycle
    result = PassingActionableValidationResult(
        validation_result_id=validation_result_id,
        validation_submission_id=validation_submission_id,
        actionable=True,
        passed=True,
        findings=(),
    )
    repository = ValidationCycleRepositorySpy(
        validation_cycle=cycle,
        accepted_submission_ids={validation_submission_id},
    )
    credit_events = CreditLifecycleEventPublisherSpy()

    updated_cycle = apply_result(
        validation_cycle_id=validation_cycle_id,
        validation_result=result,
        clock=FixedClock(transition_time),
        repository=repository,
        credit_event_publisher=credit_events,
    )

    assert original_cycle.state == "pending"
    assert updated_cycle.state == "passed-and-closed"
    assert updated_cycle.current_validation_result_id == validation_result_id
    assert updated_cycle.billable_validation_service_delivered is True
    assert repository.cycle_lookups == [validation_cycle_id]
    assert repository.association_checks == [
        (validation_cycle_id, validation_submission_id)
    ]
    assert repository.saved_cycles == [updated_cycle]
    assert len(credit_events.published_events) == 1
    event = credit_events.published_events[0]
    assert event.event_type == "billable_validation_service_delivered"
    assert event.validation_cycle_id == validation_cycle_id
    assert event.validation_result_id == validation_result_id
    assert event.previous_state == "pending"
    assert event.current_state == "passed-and-closed"
    assert event.billable_validation_service_delivered is True
    assert event.occurred_at == transition_time
