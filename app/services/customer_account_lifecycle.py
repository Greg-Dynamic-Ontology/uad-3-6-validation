"""Governed customer-account suspension and closure lifecycle."""

from __future__ import annotations

from dataclasses import replace
from enum import StrEnum
from typing import Protocol, TypeVar

from app.services.customer_accounts import (
    CustomerAccount as StoredCustomerAccount,
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


class AccountClosureObligations(Protocol):
    remaining_validation_credits: int
    validation_work_in_progress: int
    pending_purchases: int
    unresolved_payment_obligations: int


class AccountClosureObligationRepository(Protocol):
    def get_account_obligations(
        self, customer_account_id: str,
    ) -> AccountClosureObligations: ...


class DurableAccountClosureRepository(Protocol):
    def get(self, customer_account_id: str) -> StoredCustomerAccount: ...

    def close_account(
        self, *, customer_account_id: str, actor_id: str,
        expected_account: StoredCustomerAccount,
    ) -> None: ...


def request_customer_account_closure(
    *,
    actor_id: str,
    customer_account_id: str,
    confirmed: bool,
    account_repository: DurableAccountClosureRepository,
    obligation_repository: AccountClosureObligationRepository,
    audit_history: AccountAuditHistory,
) -> StoredCustomerAccount:
    """Close an active account after explicit confirmation and zero obligations.

    The application supplies a trusted obligations provider. Missing values
    must never be interpreted as zero. This boundary does not itself reconcile
    payments or serialize new purchases against closure.
    """
    if confirmed is not True:
        raise ValueError("Explicit owner confirmation is required to close the account.")
    if not isinstance(actor_id, str) or not actor_id.strip():
        raise PermissionError("An identified acting UAD user is required.")
    if not isinstance(customer_account_id, str) or not customer_account_id.strip():
        raise ValueError("An existing customer-account ID is required.")

    account = account_repository.get(customer_account_id)
    if account.customer_account_id != customer_account_id:
        raise ValueError("The repository returned a different customer account.")
    if not any(
        member.active
        and member.role == CustomerAccountRole.OWNER
        and member.human_user_id == actor_id
        and member.customer_account_id == customer_account_id
        for member in account.memberships
    ):
        raise PermissionError("An active owner in this customer account must complete closure.")
    # Authorization has already been checked. An authorized repeat reports the
    # persisted state before consulting obligations or requesting another write.
    if account.status == CustomerAccountStatus.CLOSED:
        raise ValueError("The customer account is already closed.")
    if account.status != CustomerAccountStatus.ACTIVE:
        raise ValueError("Only an active customer account can be closed.")

    obligations = obligation_repository.get_account_obligations(customer_account_id)
    fields = (
        "remaining_validation_credits",
        "validation_work_in_progress",
        "pending_purchases",
        "unresolved_payment_obligations",
    )
    blocked = []
    for name in fields:
        value = getattr(obligations, name, None)
        # This contract expresses outstanding obligations as nonnegative counts.
        # Providers must supply an explicit zero only after resolving their data.
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"Closure requires a verified nonnegative count for {name}.")
        if value:
            blocked.append(name)
    if blocked:
        raise ValueError("Account closure is blocked by: " + ", ".join(blocked) + ".")

    account_repository.close_account(
        customer_account_id=customer_account_id,
        actor_id=actor_id,
        expected_account=account,
    )
    # The adapter commits the status and durable actor/time attribution together.
    # Report success only after a confirmed persistence result.
    closed = replace(account, status=CustomerAccountStatus.CLOSED)
    audit_history.record(
        event_type="customer_account_closed",
        customer_account_id=customer_account_id,
        actor_id=actor_id,
    )
    return closed
