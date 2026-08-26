"""Executable test for IT-23R1S1 customer responsibility boundaries."""

from __future__ import annotations

from dataclasses import dataclass, field
from importlib import import_module
from typing import Any

import pytest


SUBMISSION_BOUNDARY_MODULE = "app.services.customer_submission_boundary"


@dataclass(frozen=True)
class CustomerOwnedReport:
    report_id: str
    customer_account_id: str
    content_digest: str


@dataclass(frozen=True)
class PassingValidationResult:
    validation_result_id: str
    report_id: str
    status: str = "passed"


@dataclass
class CustomerSystemOfRecordSpy:
    authoritative_report: CustomerOwnedReport
    replacement_calls: list[CustomerOwnedReport] = field(default_factory=list)
    modification_calls: list[object] = field(default_factory=list)

    def replace_authoritative_report(
        self,
        report: CustomerOwnedReport,
    ) -> None:
        self.replacement_calls.append(report)
        self.authoritative_report = report

    def modify_customer_record(self, change: object) -> None:
        self.modification_calls.append(change)


@dataclass
class GseSubmissionGatewaySpy:
    submission_calls: list[dict[str, object]] = field(default_factory=list)

    def submit_report(
        self,
        *,
        customer_account_id: str,
        report: CustomerOwnedReport,
    ) -> None:
        self.submission_calls.append(
            {
                "customer_account_id": customer_account_id,
                "report": report,
            }
        )


def _submission_boundary_contract() -> tuple[Any, Any]:
    """Load the service-boundary contract expected by IT-23R1S1."""

    try:
        module = import_module(SUBMISSION_BOUNDARY_MODULE)
    except ModuleNotFoundError as error:
        if error.name != SUBMISSION_BOUNDARY_MODULE:
            raise
        pytest.fail(
            "IT-23R1S1 requires app.services.customer_submission_boundary "
            "before customer responsibility can become green.",
            pytrace=False,
        )

    return_result = getattr(
        module,
        "return_passing_validation_result",
        None,
    )
    responsibility = getattr(
        module,
        "GseSubmissionResponsibility",
        None,
    )
    assert callable(return_result), (
        "IT-23R1S1 requires return_passing_validation_result("
        "customer_account_id, report, passing_result, system_of_record, "
        "gse_submission_gateway)."
    )
    assert responsibility is not None and hasattr(
        responsibility,
        "CUSTOMER_ACCOUNT",
    ), "IT-23R1S1 requires GseSubmissionResponsibility.CUSTOMER_ACCOUNT."
    return return_result, responsibility


def test_it_23_r1_s1_keeps_system_of_record_and_submission_with_customer() -> None:
    """Return a passing result without crossing either customer boundary."""

    return_result, responsibility = _submission_boundary_contract()
    customer_account_id = "customer-account-1"
    authoritative_report = CustomerOwnedReport(
        report_id="report-1",
        customer_account_id=customer_account_id,
        content_digest="sha256:authoritative-report",
    )
    passing_result = PassingValidationResult(
        validation_result_id="validation-result-1",
        report_id=authoritative_report.report_id,
    )
    system_of_record = CustomerSystemOfRecordSpy(authoritative_report)
    gse_submission_gateway = GseSubmissionGatewaySpy()

    delivery = return_result(
        customer_account_id,
        authoritative_report,
        passing_result,
        system_of_record,
        gse_submission_gateway,
    )

    assert delivery.validation_result is passing_result
    assert delivery.customer_account_id == customer_account_id
    assert delivery.authoritative_report_replaced is False
    assert delivery.submitted_to_gse is False
    assert (
        delivery.gse_submission_responsibility
        is responsibility.CUSTOMER_ACCOUNT
    )
    assert system_of_record.authoritative_report is authoritative_report
    assert system_of_record.replacement_calls == []
    assert system_of_record.modification_calls == []
    assert gse_submission_gateway.submission_calls == []
