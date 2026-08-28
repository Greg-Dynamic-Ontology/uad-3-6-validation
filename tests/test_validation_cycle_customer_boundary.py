"""Acceptance test for IT-25R9S1 validation-service boundaries."""

from __future__ import annotations

from dataclasses import dataclass, field
from importlib import import_module
from typing import Any


VALIDATION_CYCLES_MODULE = "app.services.validation_cycles"


@dataclass(frozen=True)
class PassedValidationCycle:
    validation_cycle_id: str
    customer_account_id: str
    report_id: str
    state: str = "passed-and-closed"


@dataclass(frozen=True)
class PassingValidationResult:
    validation_result_id: str
    report_id: str
    passed: bool = True


@dataclass
class CustomerSystemOfRecordSpy:
    modification_calls: list[object] = field(default_factory=list)
    replacement_calls: list[object] = field(default_factory=list)

    def modify_customer_record(self, change: object) -> None:
        self.modification_calls.append(change)

    def replace_authoritative_report(self, report: object) -> None:
        self.replacement_calls.append(report)


@dataclass
class GseSubmissionGatewaySpy:
    submission_calls: list[object] = field(default_factory=list)

    def submit_report(self, report: object) -> None:
        self.submission_calls.append(report)


def _passing_result_boundary_contract() -> Any:
    """Load the validation-cycle delivery contract expected by IT-25R9S1."""

    module = import_module(VALIDATION_CYCLES_MODULE)
    return_result = getattr(
        module,
        "return_passing_validation_cycle_result",
        None,
    )
    assert callable(return_result), (
        "IT-25R9S1 requires return_passing_validation_cycle_result("
        "validation_cycle, passing_result, system_of_record, "
        "gse_submission_gateway)."
    )
    return return_result


def test_it_25_r9_s1_keeps_validation_separate_from_customer_records_and_submission() -> None:
    """Return the passing result without crossing either external boundary."""

    return_result = _passing_result_boundary_contract()
    cycle = PassedValidationCycle(
        validation_cycle_id="validation-cycle-1",
        customer_account_id="customer-account-1",
        report_id="uad-report-1",
    )
    passing_result = PassingValidationResult(
        validation_result_id="validation-result-1",
        report_id=cycle.report_id,
    )
    system_of_record = CustomerSystemOfRecordSpy()
    gse_submission_gateway = GseSubmissionGatewaySpy()

    delivery = return_result(
        cycle,
        passing_result,
        system_of_record,
        gse_submission_gateway,
    )

    assert delivery.validation_result is passing_result
    assert delivery.validation_cycle_id == cycle.validation_cycle_id
    assert delivery.customer_account_id == cycle.customer_account_id
    assert delivery.authoritative_report_replaced is False
    assert delivery.submitted_to_gse is False
    assert delivery.gse_submission_responsibility == "customer account"
    assert system_of_record.modification_calls == []
    assert system_of_record.replacement_calls == []
    assert gse_submission_gateway.submission_calls == []
