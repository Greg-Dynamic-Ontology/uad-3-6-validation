"""Acceptance test for IT-25R2S1 pending validation-cycle creation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from importlib import import_module
from typing import Any
from uuid import UUID

import pytest


VALIDATION_CYCLES_MODULE = "app.services.validation_cycles"


@dataclass(frozen=True)
class UadAppraisalReport:
    report_id: str


@dataclass
class ValidationCycleIdFactoryStub:
    validation_cycle_id: str
    calls: int = 0

    def __call__(self) -> str:
        self.calls += 1
        return self.validation_cycle_id


@dataclass
class ClockStub:
    now: datetime
    calls: int = 0

    def __call__(self) -> datetime:
        self.calls += 1
        return self.now


@dataclass
class ValidationCycleRepositorySpy:
    saved_cycles: list[object] = field(default_factory=list)

    def save(self, validation_cycle: object) -> None:
        self.saved_cycles.append(validation_cycle)


def _cycle_creation_contract() -> Any:
    """Load the pending-cycle operation required by IT-25R2S1."""

    try:
        module = import_module(VALIDATION_CYCLES_MODULE)
    except ModuleNotFoundError as error:
        if error.name != VALIDATION_CYCLES_MODULE:
            raise
        pytest.fail(
            "IT-25R2S1 requires app.services.validation_cycles before "
            "pending validation-cycle creation can become green.",
            pytrace=False,
        )

    create_cycle = getattr(
        module,
        "create_pending_validation_cycle",
        None,
    )
    assert callable(create_cycle), (
        "IT-25R2S1 requires create_pending_validation_cycle("
        "customer_account_id, actor_id, report, cycle_id_factory, clock, "
        "repository)."
    )
    return create_cycle


def test_it_25_r2_s1_creates_a_pending_cycle_for_a_new_report() -> None:
    """Create one globally identified cycle in the customer's scope."""

    create_cycle = _cycle_creation_contract()
    customer_account_id = "customer-account-1"
    actor_id = "human-user-validator"
    report = UadAppraisalReport(report_id="uad-report-1")
    generated_cycle_id = "6ad8df4d-df4a-4a2f-925e-2f57df436c92"
    cycle_id_factory = ValidationCycleIdFactoryStub(generated_cycle_id)
    accepted_at = datetime(2026, 8, 27, 15, 30, tzinfo=timezone.utc)
    clock = ClockStub(accepted_at)
    repository = ValidationCycleRepositorySpy()

    result = create_cycle(
        customer_account_id,
        actor_id,
        report,
        cycle_id_factory,
        clock,
        repository,
    )

    assert UUID(result.validation_cycle_id) == UUID(generated_cycle_id)
    assert result.customer_account_id == customer_account_id
    assert result.actor_id == actor_id
    assert result.state == "pending"
    assert result.report_id == report.report_id
    assert result.created_at == accepted_at
    assert repository.saved_cycles == [result]
    assert cycle_id_factory.calls == 1
    assert clock.calls == 1
