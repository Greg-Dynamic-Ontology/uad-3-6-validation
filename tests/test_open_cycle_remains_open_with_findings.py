"""Acceptance test for IT-25R6S1 corrected report with findings."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from importlib import import_module
from typing import Any


VALIDATION_CYCLES_MODULE = "app.services.validation_cycles"


@dataclass(frozen=True)
class ValidationFinding:
    requirement_id: str
    message: str


@dataclass(frozen=True)
class CorrectedActionableValidationResult:
    validation_result_id: str
    validation_submission_id: str
    actionable: bool
    passed: bool
    findings: tuple[ValidationFinding, ...]


@dataclass
class ValidationCycleRepositorySpy:
    validation_cycle: object
    accepted_submission_ids: set[str]
    result_history: list[str]
    cycle_lookups: list[str] = field(default_factory=list)
    association_checks: list[tuple[str, str]] = field(default_factory=list)
    saved_cycles: list[object] = field(default_factory=list)
    appended_results: list[tuple[str, str]] = field(default_factory=list)

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

    def append_result_history(
        self,
        validation_cycle_id: str,
        validation_result_id: str,
    ) -> None:
        self.appended_results.append(
            (validation_cycle_id, validation_result_id)
        )
        self.result_history.append(validation_result_id)


def _corrected_result_contract() -> tuple[Any, type[Any]]:
    """Load the corrected-result lifecycle contract for IT-25R6S1."""

    module = import_module(VALIDATION_CYCLES_MODULE)
    apply_result = getattr(
        module,
        "apply_corrected_actionable_validation_result",
        None,
    )
    cycle_type = getattr(module, "PendingValidationCycle", None)
    assert callable(apply_result), (
        "IT-25R6S1 requires "
        "apply_corrected_actionable_validation_result("
        "validation_cycle_id, validation_result, repository)."
    )
    assert isinstance(cycle_type, type)
    return apply_result, cycle_type


def test_it_25_r6_s1_keeps_open_cycle_open_while_findings_remain() -> None:
    """Make the correction current without discarding the earlier result."""

    apply_result, cycle_type = _corrected_result_contract()
    validation_cycle_id = "6ad8df4d-df4a-4a2f-925e-2f57df436c92"
    corrected_submission_id = "c4a41d23-3369-46d6-a5c1-ae580ee62281"
    prior_result_id = "validation-result-with-findings-1"
    corrected_result_id = "validation-result-with-findings-2"
    cycle = cycle_type(
        validation_cycle_id=validation_cycle_id,
        customer_account_id="customer-account-1",
        actor_id="human-user-validator",
        report_id="uad-report-1",
        state="open",
        created_at=datetime(2026, 8, 27, 17, 30, tzinfo=timezone.utc),
        current_validation_result_id=prior_result_id,
        billable_validation_service_delivered=True,
    )
    original_cycle = cycle
    result = CorrectedActionableValidationResult(
        validation_result_id=corrected_result_id,
        validation_submission_id=corrected_submission_id,
        actionable=True,
        passed=False,
        findings=(
            ValidationFinding(
                requirement_id="UAD36-CONSTRAINT-QUALITY-1",
                message="The corrected report still has an invalid value.",
            ),
        ),
    )
    repository = ValidationCycleRepositorySpy(
        validation_cycle=cycle,
        accepted_submission_ids={corrected_submission_id},
        result_history=[prior_result_id],
    )

    updated_cycle = apply_result(
        validation_cycle_id=validation_cycle_id,
        validation_result=result,
        repository=repository,
    )

    assert original_cycle.state == "open"
    assert original_cycle.current_validation_result_id == prior_result_id
    assert updated_cycle.state == "open"
    assert updated_cycle.current_validation_result_id == corrected_result_id
    assert repository.cycle_lookups == [validation_cycle_id]
    assert repository.association_checks == [
        (validation_cycle_id, corrected_submission_id)
    ]
    assert repository.saved_cycles == [updated_cycle]
    assert repository.appended_results == [
        (validation_cycle_id, corrected_result_id)
    ]
    assert repository.result_history == [prior_result_id, corrected_result_id]
