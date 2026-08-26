"""Governed customer-account suspension and closure lifecycle."""

from __future__ import annotations

from dataclasses import replace
from enum import StrEnum
from typing import Protocol, TypeVar

from app.services.customer_accounts import (
    CustomerAccountMembership,
    CustomerAccountRole,
)


class CustomerAccountStatus(StrEnum):
    """Governed lifecycle states for a customer account."""

    ACTIVE = "active"
    SUSPENDED = "suspended"
    CLOSED = "closed"


class CustomerAccountLifecycleActivity(StrEnum):
    """Activities affected by customer-account lifecycle state."""

    OPEN_NEW_VALIDATION_CYCLE = "open new validation cycle"
    PURCHASE_RETAIL_CREDITS = "purchase retail credits"
    REVIEW_GOVERNED_RECORDS = "review governed records"


class GovernedCustomerAccount(Protocol):
    customer_account_id: str
    status: CustomerAccountStatus


CustomerAccount = TypeVar("CustomerAccount", bound=GovernedCustomerAccount)


class CustomerAccountRepository(Protocol[CustomerAccount]):
    def save(self, customer_account: CustomerAccount) -> None: ...


class AccountAuditHistory(Protocol):
    def record(self, **event: str) -> None: ...


class SuspensionPolicy(Protocol):
    def allows(self, activity: CustomerAccountLifecycleActivity) -> bool: ...


class ClosableCustomerAccount(GovernedCustomerAccount, Protocol):
    eligible_for_closure: bool
    records: object
    unused_credit_quantity: int
    outstanding_financial_obligation: int
    billing_resolution: str | None


ClosableAccount = TypeVar("ClosableAccount", bound=ClosableCustomerAccount)


class GovernedRecordPolicy(Protocol):
    def apply(
        self,
        customer_account_id: str,
        records: object,
    ) -> object: ...


class BillingClosurePolicy(Protocol):
    def resolve(
        self,
        customer_account_id: str,
        unused_credit_quantity: int,
        outstanding_financial_obligation: int,
    ) -> str: ...


_SUSPENDED_OPERATIONAL_BLOCKS = frozenset(
    {
        CustomerAccountLifecycleActivity.OPEN_NEW_VALIDATION_CYCLE,
        CustomerAccountLifecycleActivity.PURCHASE_RETAIL_CREDITS,
    }
)


def suspend_customer_account(
    administrator_id: str,
    customer_account: CustomerAccount,
    repository: CustomerAccountRepository[CustomerAccount],
    audit_history: AccountAuditHistory,
) -> CustomerAccount:
    """Suspend an active account without modifying its governed records."""

    if customer_account.status is not CustomerAccountStatus.ACTIVE:
        raise ValueError("Only an active customer account can be suspended.")

    suspended_account = replace(
        customer_account,
        status=CustomerAccountStatus.SUSPENDED,
    )
    repository.save(suspended_account)
    audit_history.record(
        event_type="customer_account_suspended",
        customer_account_id=customer_account.customer_account_id,
        actor_id=administrator_id,
    )
    return suspended_account


def authorize_account_activity_during_suspension(
    customer_account: GovernedCustomerAccount,
    actor_id: str,
    activity: CustomerAccountLifecycleActivity,
    suspension_policy: SuspensionPolicy,
) -> bool:
    """Block new operations and delegate retained-record access to policy."""

    del actor_id
    if customer_account.status is not CustomerAccountStatus.SUSPENDED:
        return False
    if activity in _SUSPENDED_OPERATIONAL_BLOCKS:
        return False
    return suspension_policy.allows(activity)


def close_customer_account(
    owner_membership: CustomerAccountMembership,
    customer_account: ClosableAccount,
    governed_record_policy: GovernedRecordPolicy,
    billing_policy: BillingClosurePolicy,
    repository: CustomerAccountRepository[ClosableAccount],
    audit_history: AccountAuditHistory,
) -> ClosableAccount:
    """Close an eligible account through explicit records and billing policy."""

    owner_is_authorized = (
        owner_membership.active
        and owner_membership.role is CustomerAccountRole.OWNER
        and owner_membership.customer_account_id
        == customer_account.customer_account_id
    )
    if not owner_is_authorized:
        raise PermissionError(
            "An active owner in this customer account must complete closure."
        )
    if not customer_account.eligible_for_closure:
        raise ValueError("The customer account is not eligible for closure.")
    if customer_account.status is CustomerAccountStatus.CLOSED:
        raise ValueError("The customer account is already closed.")

    governed_records = governed_record_policy.apply(
        customer_account.customer_account_id,
        customer_account.records,
    )
    billing_resolution = billing_policy.resolve(
        customer_account.customer_account_id,
        customer_account.unused_credit_quantity,
        customer_account.outstanding_financial_obligation,
    )
    closed_account = replace(
        customer_account,
        status=CustomerAccountStatus.CLOSED,
        records=governed_records,
        billing_resolution=billing_resolution,
    )
    repository.save(closed_account)
    audit_history.record(
        event_type="customer_account_closed",
        customer_account_id=customer_account.customer_account_id,
        actor_id=owner_membership.human_user_id,
    )
    return closed_account
