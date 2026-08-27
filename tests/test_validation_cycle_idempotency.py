"""Acceptance test for IT-25R2S3 idempotent cycle creation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from importlib import import_module
from typing import Any

import pytest


VALIDATION_CYCLES_MODULE = "app.services.validation_cycles"


@dataclass(frozen=True)
class UadAppraisalReport:
    report_id: str


@dataclass
class IdempotencyRepositoryStub:
    existing_cycle: object
    lookups: list[tuple[str, str]] = field(default_factory=list)
    saved_records: list[tuple[str, str, object]] = field(
        default_factory=list
    )

    def get(
        self,
        customer_account_id: str,
        idempotency_key: str,
    ) -> object:
        self.lookups.append((customer_account_id, idempotency_key))
        return self.existing_cycle

    def save(
        self,
        customer_account_id: str,
        idempotency_key: str,
        validation_cycle: object,
    ) -> None:
        self.saved_records.append(
            (
                customer_account_id,
                idempotency_key,
                validation_cycle,
            )
        )


@dataclass
class ValidationAuthorizationSpy:
    calls: list[tuple[str, str]] = field(default_factory=list)

    def authorize_new_cycle(
        self,
        customer_account_id: str,
        actor_id: str,
    ) -> None:
        self.calls.append((customer_account_id, actor_id))


@dataclass
class ValidationCycleRepositorySpy:
    saved_cycles: list[object] = field(default_factory=list)

    def save(self, validation_cycle: object) -> None:
        self.saved_cycles.append(validation_cycle)


@dataclass
class UnexpectedCallStub:
    calls: int = 0

    def __call__(self) -> object:
        self.calls += 1
        raise AssertionError(
            "IT-25R2S3 must reuse the existing cycle on replay."
        )


def _idempotency_contract() -> tuple[Any, type[Any]]:
    """Load the idempotent creation contract required by IT-25R2S3."""

    try:
        module = import_module(VALIDATION_CYCLES_MODULE)
    except ModuleNotFoundError as error:
        if error.name != VALIDATION_CYCLES_MODULE:
            raise
        pytest.fail(
            "IT-25R2S3 requires app.services.validation_cycles before "
            "idempotent cycle creation can become green.",
            pytrace=False,
        )

    create_idempotently = getattr(
        module,
        "create_pending_validation_cycle_idempotently",
        None,
    )
    pending_cycle = getattr(module, "PendingValidationCycle", None)
    assert callable(create_idempotently), (
        "IT-25R2S3 requires "
        "create_pending_validation_cycle_idempotently(...)."
    )
    assert isinstance(pending_cycle, type)
    return create_idempotently, pending_cycle


def test_it_25_r2_s3_replays_a_cycle_request_idempotently() -> None:
    """Return the existing cycle without repeating authorized work."""

    create_idempotently, pending_cycle = _idempotency_contract()
    customer_account_id = "customer-account-1"
    actor_id = "human-user-validator"
    idempotency_key = "new-report-request-92851"
    existing_cycle = pending_cycle(
        validation_cycle_id="6ad8df4d-df4a-4a2f-925e-2f57df436c92",
        customer_account_id=customer_account_id,
        actor_id=actor_id,
        report_id="uad-report-1",
        state="pending",
        created_at=datetime(
            2026,
            8,
            27,
            15,
            30,
            tzinfo=timezone.utc,
        ),
    )
    idempotency_repository = IdempotencyRepositoryStub(existing_cycle)
    authorization = ValidationAuthorizationSpy()
    cycle_repository = ValidationCycleRepositorySpy()
    cycle_id_factory = UnexpectedCallStub()
    clock = UnexpectedCallStub()

    result = create_idempotently(
        customer_account_id=customer_account_id,
        actor_id=actor_id,
        report=UadAppraisalReport(report_id="uad-report-1"),
        idempotency_key=idempotency_key,
        authorization=authorization,
        idempotency_repository=idempotency_repository,
        cycle_id_factory=cycle_id_factory,
        clock=clock,
        cycle_repository=cycle_repository,
    )

    assert result is existing_cycle
    assert result.validation_cycle_id == (
        existing_cycle.validation_cycle_id
    )
    assert idempotency_repository.lookups == [
        (customer_account_id, idempotency_key)
    ]
    assert idempotency_repository.saved_records == []
    assert authorization.calls == []
    assert cycle_repository.saved_cycles == []
    assert cycle_id_factory.calls == 0
    assert clock.calls == 0
