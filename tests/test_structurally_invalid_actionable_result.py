"""Acceptance test for IT-25R4S1 actionable structural findings."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from importlib import import_module
from typing import Any
from uuid import UUID


VALIDATION_CYCLES_MODULE = "app.services.validation_cycles"


@dataclass(frozen=True)
class StructuralValidationFinding:
    requirement_id: str
    message: str
    data_location: str


@dataclass(frozen=True)
class CompletedValidatorResult:
    ingestible: bool
    findings: tuple[StructuralValidationFinding, ...]


@dataclass
class FixedFactory:
    value: str
    calls: int = 0

    def __call__(self) -> str:
        self.calls += 1
        return self.value


@dataclass
class FixedClock:
    value: datetime

    def __call__(self) -> datetime:
        return self.value


@dataclass
class ValidationResultRepositorySpy:
    saved_results: list[object] = field(default_factory=list)

    def save_result(self, validation_result: object) -> None:
        self.saved_results.append(validation_result)


def _actionable_result_contract() -> Any:
    """Load the actionable-result contract required by IT-25R4S1."""

    module = import_module(VALIDATION_CYCLES_MODULE)
    produce_result = getattr(
        module,
        "produce_actionable_validation_result",
        None,
    )
    assert callable(produce_result), (
        "IT-25R4S1 requires produce_actionable_validation_result("
        "validation_submission_id, validator_result, result_id_factory, "
        "clock, repository)."
    )
    return produce_result


def test_it_25_r4_s1_makes_structural_invalidity_actionable() -> None:
    """Return and retain identifiable findings for the exact submission."""

    produce_result = _actionable_result_contract()
    validation_submission_id = "66a29861-f6d6-4572-91de-ce32d28a8421"
    validation_result_id = "26b2f152-8176-48cf-b397-8ec662a528e3"
    completed_at = datetime(2026, 8, 27, 17, 0, tzinfo=timezone.utc)
    findings = (
        StructuralValidationFinding(
            requirement_id="UAD36-SCHEMA-ADDRESS-1",
            message="Property address is missing a required postal code.",
            data_location="/REPORT/PROPERTY/ADDRESS/POSTAL_CODE",
        ),
    )
    validator_result = CompletedValidatorResult(
        ingestible=True,
        findings=findings,
    )
    result_id_factory = FixedFactory(validation_result_id)
    repository = ValidationResultRepositorySpy()

    result = produce_result(
        validation_submission_id=validation_submission_id,
        validator_result=validator_result,
        result_id_factory=result_id_factory,
        clock=FixedClock(completed_at),
        repository=repository,
    )

    assert UUID(result.validation_result_id) == UUID(validation_result_id)
    assert result.validation_submission_id == validation_submission_id
    assert result.actionable is True
    assert result.passed is False
    assert result.findings == findings
    assert result.findings[0].requirement_id
    assert result.findings[0].message
    assert result.findings[0].data_location
    assert result.completed_at == completed_at
    assert result_id_factory.calls == 1
    assert repository.saved_results == [result]
