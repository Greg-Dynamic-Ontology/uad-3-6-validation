"""Executable test for IT-21R1S2 governed customer-account closure."""

from __future__ import annotations

from dataclasses import dataclass, field
from importlib import import_module
from typing import Any

from app.services.customer_account_lifecycle import (
    CustomerAccountLifecycleActivity,
    CustomerAccountStatus,
    authorize_account_activity_during_suspension,
)
from app.services.customer_accounts import (
    CustomerAccountMembership,
    CustomerAccountRole,
)


ACCOUNT_LIFECYCLE_MODULE = "app.services.customer_account_lifecycle"


@dataclass(frozen=True)
class GovernedRecord:
    record_id: str
    customer_account_id: str


@dataclass(frozen=True)
class GovernedAccountRecords:
    reports: tuple[GovernedRecord, ...]
    validation_cycles: tuple[GovernedRecord, ...]
    findings: tuple[GovernedRecord, ...]
    billing_records: tuple[GovernedRecord, ...]
    audit_history: tuple[GovernedRecord, ...]


@dataclass(frozen=True)
class ClosableCustomerAccount:
    customer_account_id: str
    status: CustomerAccountStatus
    eligible_for_closure: bool
    records: GovernedAccountRecords
    unused_credit_quantity: int
    outstanding_financial_obligation: int
    billing_resolution: str | None = None


@dataclass
class GovernedRecordPolicySpy:
    calls: list[tuple[str, GovernedAccountRecords]] = field(
        default_factory=list
    )

    def apply(
        self,
        customer_account_id: str,
        records: GovernedAccountRecords,
    ) -> GovernedAccountRecords:
        self.calls.append((customer_account_id, records))
        return records


@dataclass
class BillingClosurePolicySpy:
    calls: list[dict[str, int | str]] = field(default_factory=list)

    def resolve(
        self,
        customer_account_id: str,
        unused_credit_quantity: int,
        outstanding_financial_obligation: int,
    ) -> str:
        self.calls.append(
            {
                "customer_account_id": customer_account_id,
                "unused_credit_quantity": unused_credit_quantity,
                "outstanding_financial_obligation": (
                    outstanding_financial_obligation
                ),
            }
        )
        return "unused credits refunded; outstanding balance invoiced"


@dataclass
class CustomerAccountRepositorySpy:
    saved_accounts: list[ClosableCustomerAccount] = field(
        default_factory=list
    )

    def save(self, customer_account: ClosableCustomerAccount) -> None:
        self.saved_accounts.append(customer_account)


@dataclass
class AccountAuditHistorySpy:
    events: list[dict[str, str]]

    def record(self, **event: str) -> None:
        self.events.append(event)


@dataclass
class UnexpectedClosedAccountPolicy:
    def allows(self, activity: CustomerAccountLifecycleActivity) -> bool:
        raise AssertionError(
            f"Closed account activity must not reach policy: {activity}"
        )


def _account_closure_contract() -> Any:
    """Load the account-closure contract expected by IT-21R1S2."""

    module = import_module(ACCOUNT_LIFECYCLE_MODULE)
    close_account = getattr(module, "close_customer_account", None)
    assert callable(close_account), (
        "IT-21R1S2 requires close_customer_account(owner_membership, "
        "customer_account, governed_record_policy, billing_policy, "
        "repository, audit_history)."
    )
    return close_account


def test_it_21_r1_s2_closes_account_without_silent_record_deletion() -> None:
    """Close operations while policies govern records and finances."""

    close_account = _account_closure_contract()
    customer_account_id = "customer-account-1"
    owner = CustomerAccountMembership(
        human_user_id="human-user-owner",
        customer_account_id=customer_account_id,
        role=CustomerAccountRole.OWNER,
        active=True,
    )

    def record(category: str) -> tuple[GovernedRecord, ...]:
        return (GovernedRecord(f"{category}-1", customer_account_id),)

    records = GovernedAccountRecords(
        reports=record("report"),
        validation_cycles=record("validation-cycle"),
        findings=record("finding"),
        billing_records=record("billing-record"),
        audit_history=record("audit-record"),
    )
    account = ClosableCustomerAccount(
        customer_account_id=customer_account_id,
        status=CustomerAccountStatus.ACTIVE,
        eligible_for_closure=True,
        records=records,
        unused_credit_quantity=2,
        outstanding_financial_obligation=75,
    )
    governed_record_policy = GovernedRecordPolicySpy()
    billing_policy = BillingClosurePolicySpy()
    repository = CustomerAccountRepositorySpy()
    prior_audit_event = {
        "event_type": "account_created",
        "customer_account_id": customer_account_id,
        "actor_id": owner.human_user_id,
    }
    audit_history = AccountAuditHistorySpy(events=[prior_audit_event])

    closed_account = close_account(
        owner,
        account,
        governed_record_policy,
        billing_policy,
        repository,
        audit_history,
    )

    assert closed_account.status is CustomerAccountStatus.CLOSED
    assert closed_account.records == records
    assert governed_record_policy.calls == [(customer_account_id, records)]
    assert billing_policy.calls == [
        {
            "customer_account_id": customer_account_id,
            "unused_credit_quantity": 2,
            "outstanding_financial_obligation": 75,
        }
    ]
    assert closed_account.billing_resolution == (
        "unused credits refunded; outstanding balance invoiced"
    )
    assert repository.saved_accounts == [closed_account]

    for actor_id in ("human-user-1", "software-client-1"):
        assert authorize_account_activity_during_suspension(
            closed_account,
            actor_id,
            CustomerAccountLifecycleActivity.OPEN_NEW_VALIDATION_CYCLE,
            UnexpectedClosedAccountPolicy(),
        ) is False
    assert audit_history.events == [
        prior_audit_event,
        {
            "event_type": "customer_account_closed",
            "customer_account_id": customer_account_id,
            "actor_id": owner.human_user_id,
        },
    ]
