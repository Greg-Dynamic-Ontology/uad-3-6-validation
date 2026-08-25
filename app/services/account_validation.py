"""Account-scoped entry points for report validation."""

from __future__ import annotations

from typing import Protocol, TypeVar

from app.services.account_authorization import (
    AuthorizationResult,
    CustomerAccountActivity,
    authorize_customer_activity,
)
from app.services.customer_accounts import CustomerAccountMembership


class UadAppraisalReport(Protocol):
    """Minimum report identity required to begin validation."""

    report_id: str


ValidationStartResult = TypeVar("ValidationStartResult")


class ValidationCycleGateway(Protocol[ValidationStartResult]):
    """Boundary owned by the report-validation-cycle capability."""

    def start_new_report_validation(
        self,
        *,
        report_id: str,
        customer_account_id: str,
        actor_id: str,
    ) -> ValidationStartResult: ...


def submit_report_for_customer_validation(
    membership: CustomerAccountMembership,
    customer_account_id: str,
    report: UadAppraisalReport,
    validation_gateway: ValidationCycleGateway[ValidationStartResult],
) -> ValidationStartResult:
    """Submit a report with its authorized account and human actor scope."""

    decision = authorize_customer_activity(
        membership,
        customer_account_id,
        CustomerAccountActivity.SUBMIT_REPORTS_AND_MANAGE_VALIDATION_CYCLES,
    )
    if decision.result is AuthorizationResult.DENIED:
        raise PermissionError(
            "An active validator membership is required for this account."
        )

    return validation_gateway.start_new_report_validation(
        report_id=report.report_id,
        customer_account_id=customer_account_id,
        actor_id=membership.human_user_id,
    )
