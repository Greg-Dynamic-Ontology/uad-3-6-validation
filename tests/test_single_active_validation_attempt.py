"""Acceptance test for IT-25R3S4 single active validation attempt."""

from __future__ import annotations

from dataclasses import dataclass, field
from importlib import import_module
from typing import Any

import pytest


VALIDATION_CYCLES_MODULE = "app.services.validation_cycles"


@dataclass(frozen=True)
class ActiveValidationAttempt:
    validation_attempt_id: str
    validation_cycle_id: str
    validation_submission_id: str
    state: str


@dataclass
class ValidationAttemptRepositorySpy:
    active_attempt: ActiveValidationAttempt
    current_result_id: str
    active_lookups: list[str] = field(default_factory=list)
    saved_attempts: list[object] = field(default_factory=list)
    saved_results: list[object] = field(default_factory=list)

    def get_active_for_cycle(
        self,
        validation_cycle_id: str,
    ) -> ActiveValidationAttempt:
        self.active_lookups.append(validation_cycle_id)
        return self.active_attempt

    def save_attempt(self, validation_attempt: object) -> None:
        self.saved_attempts.append(validation_attempt)

    def save_result(self, validation_result: object) -> None:
        self.saved_results.append(validation_result)


@dataclass
class UnexpectedCallStub:
    calls: int = 0

    def __call__(self, *args: object, **kwargs: object) -> object:
        self.calls += 1
        raise AssertionError(
            "IT-25R3S4 must not begin a concurrent validation attempt."
        )


def _single_attempt_contract() -> tuple[Any, type[Exception]]:
    """Load the attempt-concurrency contract required by IT-25R3S4."""

    module = import_module(VALIDATION_CYCLES_MODULE)
    start_attempt = getattr(module, "start_validation_attempt", None)
    active_attempt_error = getattr(
        module,
        "ValidationAttemptAlreadyActiveError",
        None,
    )
    assert callable(start_attempt), (
        "IT-25R3S4 requires start_validation_attempt("
        "validation_cycle_id, validation_submission_id, "
        "attempt_id_factory, clock, validation_runner, repository)."
    )
    assert (
        isinstance(active_attempt_error, type)
        and issubclass(active_attempt_error, Exception)
    ), "IT-25R3S4 requires ValidationAttemptAlreadyActiveError."
    return start_attempt, active_attempt_error


def test_it_25_r3_s4_rejects_a_second_active_validation_attempt() -> None:
    """Keep the running attempt authoritative until it completes."""

    start_attempt, active_attempt_error = _single_attempt_contract()
    validation_cycle_id = "6ad8df4d-df4a-4a2f-925e-2f57df436c92"
    active_attempt = ActiveValidationAttempt(
        validation_attempt_id="validation-attempt-active-1",
        validation_cycle_id=validation_cycle_id,
        validation_submission_id="validation-submission-active-1",
        state="running",
    )
    repository = ValidationAttemptRepositorySpy(
        active_attempt=active_attempt,
        current_result_id="validation-result-current-1",
    )
    attempt_id_factory = UnexpectedCallStub()
    clock = UnexpectedCallStub()
    validation_runner = UnexpectedCallStub()

    with pytest.raises(
        active_attempt_error,
        match="active validation attempt",
    ):
        start_attempt(
            validation_cycle_id=validation_cycle_id,
            validation_submission_id="validation-submission-second-1",
            attempt_id_factory=attempt_id_factory,
            clock=clock,
            validation_runner=validation_runner,
            repository=repository,
        )

    assert repository.active_lookups == [validation_cycle_id]
    assert repository.active_attempt == active_attempt
    assert repository.saved_attempts == []
    assert repository.saved_results == []
    assert repository.current_result_id == "validation-result-current-1"
    assert attempt_id_factory.calls == 0
    assert clock.calls == 0
    assert validation_runner.calls == 0
