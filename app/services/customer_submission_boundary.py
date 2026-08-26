"""Boundary between validation delivery and customer/GSE responsibilities."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol


class CustomerOwnedReport(Protocol):
    report_id: str
    customer_account_id: str


class PassingValidationResult(Protocol):
    report_id: str
    status: str


class CustomerSystemOfRecord(Protocol):
    """Marker for the external customer-controlled system of record."""


class GseSubmissionGateway(Protocol):
    """Marker for submission capability outside the validation boundary."""


class GseSubmissionResponsibility(StrEnum):
    """Party responsible for submitting a validated report to a GSE."""

    CUSTOMER_ACCOUNT = "customer account"


@dataclass(frozen=True)
class PassingValidationResultDelivery:
    """A passing result returned without external side effects."""

    validation_result: PassingValidationResult
    customer_account_id: str
    authoritative_report_replaced: bool
    submitted_to_gse: bool
    gse_submission_responsibility: GseSubmissionResponsibility


def return_passing_validation_result(
    customer_account_id: str,
    report: CustomerOwnedReport,
    passing_result: PassingValidationResult,
    system_of_record: CustomerSystemOfRecord,
    gse_submission_gateway: GseSubmissionGateway,
) -> PassingValidationResultDelivery:
    """Deliver a passing result without writing or submitting externally."""

    if report.customer_account_id != customer_account_id:
        raise PermissionError(
            "The report is not owned by the acting customer account."
        )
    if passing_result.report_id != report.report_id:
        raise ValueError("The validation result belongs to another report.")
    if passing_result.status != "passed":
        raise ValueError("Only a passing validation result can be delivered.")

    # These collaborators intentionally remain untouched. Their presence makes
    # the service boundary explicit and prevents delivery from implying writes
    # to the customer's system or submission to a GSE.
    del system_of_record, gse_submission_gateway

    return PassingValidationResultDelivery(
        validation_result=passing_result,
        customer_account_id=customer_account_id,
        authoritative_report_replaced=False,
        submitted_to_gse=False,
        gse_submission_responsibility=(
            GseSubmissionResponsibility.CUSTOMER_ACCOUNT
        ),
    )
