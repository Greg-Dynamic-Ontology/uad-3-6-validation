"""Role-based authorization within a customer-account boundary."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from app.services.customer_accounts import (
    CustomerAccountMembership,
    CustomerAccountRole,
)


class CustomerAccountActivity(StrEnum):
    """Customer-account activities governed by implemented role rules."""

    MANAGE_MEMBERSHIP_AND_ACCOUNT_CLOSURE = (
        "manage membership and account closure"
    )
    PURCHASE_CREDITS_AND_VIEW_FINANCIAL_HISTORY = (
        "purchase credits and view financial history"
    )
    PURCHASE_VALIDATION_CREDITS = "purchase validation credits"
    VIEW_CREDIT_BALANCES_AND_LEDGER_ACTIVITY = (
        "view credit balances and credit-ledger activity"
    )
    VIEW_PAYMENT_REFUND_AND_INVOICE_HISTORY = (
        "view payment, refund, and invoice history"
    )
    SUBMIT_REPORTS_AND_MANAGE_VALIDATION_CYCLES = (
        "submit reports and manage validation cycles"
    )
    VIEW_REPORTS_FINDINGS_AND_CYCLE_HISTORIES = (
        "view reports, findings, and cycle histories"
    )
    SUBMIT_REPORT_FOR_NEW_VALIDATION_CYCLE = (
        "submit report for new validation cycle"
    )
    CLOSE_CUSTOMER_ACCOUNT = "close customer account"
    CREATE_VALIDATION_CYCLE = "create validation cycle"
    MODIFY_REPORTS = "modify reports"
    MODIFY_FINDINGS = "modify findings"
    MODIFY_CREDITS = "modify credits"
    MODIFY_BILLING = "modify billing"
    MODIFY_MEMBERSHIP = "modify membership"


class AuthorizationResult(StrEnum):
    """Possible outcomes of an account authorization decision."""

    ALLOWED = "allowed"
    DENIED = "denied"


@dataclass(frozen=True)
class CustomerAccountAuthorizationDecision:
    """The result of evaluating an activity within one account."""

    result: AuthorizationResult
    customer_account_id: str


class ActiveCustomerAccount(Protocol):
    """Account boundary required when evaluating a protected request."""

    customer_account_id: str
    active: bool


class AccountAuditHistory(Protocol):
    """Audit boundary for customer-account authorization events."""

    def record(self, **event: str) -> None: ...


_ALLOWED_ACTIVITIES = {
    CustomerAccountRole.OWNER: {
        CustomerAccountActivity.MANAGE_MEMBERSHIP_AND_ACCOUNT_CLOSURE,
    },
    CustomerAccountRole.BILLING_ADMINISTRATOR: {
        CustomerAccountActivity.PURCHASE_CREDITS_AND_VIEW_FINANCIAL_HISTORY,
        CustomerAccountActivity.PURCHASE_VALIDATION_CREDITS,
        CustomerAccountActivity.VIEW_CREDIT_BALANCES_AND_LEDGER_ACTIVITY,
        CustomerAccountActivity.VIEW_PAYMENT_REFUND_AND_INVOICE_HISTORY,
    },
    CustomerAccountRole.VALIDATOR: {
        CustomerAccountActivity.SUBMIT_REPORTS_AND_MANAGE_VALIDATION_CYCLES,
    },
    CustomerAccountRole.REVIEWER: {
        CustomerAccountActivity.VIEW_REPORTS_FINDINGS_AND_CYCLE_HISTORIES,
    },
}


def authorize_customer_activity(
    membership: CustomerAccountMembership,
    customer_account_id: str,
    activity: CustomerAccountActivity,
) -> CustomerAccountAuthorizationDecision:
    """Authorize an active membership only within its own customer account."""

    is_allowed = (
        membership.active
        and membership.customer_account_id == customer_account_id
        and activity in _ALLOWED_ACTIVITIES.get(membership.role, set())
    )
    return CustomerAccountAuthorizationDecision(
        result=(
            AuthorizationResult.ALLOWED
            if is_allowed
            else AuthorizationResult.DENIED
        ),
        customer_account_id=customer_account_id,
    )


def request_customer_account_activity(
    membership: CustomerAccountMembership,
    customer_account: ActiveCustomerAccount,
    activity: CustomerAccountActivity,
    audit_history: AccountAuditHistory,
) -> CustomerAccountAuthorizationDecision:
    """Evaluate a protected request and audit a denial without changing state."""

    decision = authorize_customer_activity(
        membership,
        customer_account.customer_account_id,
        activity,
    )
    if decision.result is AuthorizationResult.DENIED:
        audit_history.record(
            event_type="customer_account_activity_denied",
            customer_account_id=customer_account.customer_account_id,
            actor_id=membership.human_user_id,
            activity=activity.value,
        )
    return decision
