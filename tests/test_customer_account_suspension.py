"""Executable test for IT-21R1S1 customer-account suspension."""

from __future__ import annotations

from dataclasses import dataclass, field
from importlib import import_module
from typing import Any

import pytest


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
    credits: tuple[GovernedRecord, ...]
    billing_records: tuple[GovernedRecord, ...]
    audit_history: tuple[GovernedRecord, ...]


@dataclass(frozen=True)
class GovernedCustomerAccount:
    customer_account_id: str
    status: object
    records: GovernedAccountRecords


@dataclass
class CustomerAccountRepositorySpy:
    saved_accounts: list[GovernedCustomerAccount] = field(default_factory=list)

    def save(self, customer_account: GovernedCustomerAccount) -> None:
        self.saved_accounts.append(customer_account)


@dataclass
class AccountAuditHistorySpy:
    events: list[dict[str, str]]

    def record(self, **event: str) -> None:
        self.events.append(event)


@dataclass
class SuspensionPolicySpy:
    evaluated_activities: list[object] = field(default_factory=list)

    def allows(self, activity: object) -> bool:
        self.evaluated_activities.append(activity)
        return getattr(activity, "name", "") == "REVIEW_GOVERNED_RECORDS"


def _account_suspension_contract() -> tuple[Any, Any, Any, Any]:
    """Load the account-suspension contract expected by IT-21R1S1."""

    try:
        module = import_module(ACCOUNT_LIFECYCLE_MODULE)
    except ModuleNotFoundError as error:
        if error.name != ACCOUNT_LIFECYCLE_MODULE:
            raise
        pytest.fail(
            "IT-21R1S1 requires app.services.customer_account_lifecycle "
            "before suspension can become green.",
            pytrace=False,
        )

    suspend_account = getattr(module, "suspend_customer_account", None)
    authorize_activity = getattr(
        module,
        "authorize_account_activity_during_suspension",
        None,
    )
    account_status = getattr(module, "CustomerAccountStatus", None)
    lifecycle_activity = getattr(
        module,
        "CustomerAccountLifecycleActivity",
        None,
    )
    assert callable(suspend_account), (
        "IT-21R1S1 requires suspend_customer_account(administrator_id, "
        "customer_account, repository, audit_history)."
    )
    assert callable(authorize_activity), (
        "IT-21R1S1 requires authorize_account_activity_during_suspension("
        "customer_account, actor_id, activity, suspension_policy)."
    )
    assert account_status is not None and hasattr(
        account_status,
        "ACTIVE",
    ) and hasattr(account_status, "SUSPENDED")
    assert lifecycle_activity is not None
    for activity_name in (
        "OPEN_NEW_VALIDATION_CYCLE",
        "PURCHASE_RETAIL_CREDITS",
        "REVIEW_GOVERNED_RECORDS",
    ):
        assert hasattr(lifecycle_activity, activity_name)
    return (
        suspend_account,
        authorize_activity,
        account_status,
        lifecycle_activity,
    )


def test_it_21_r1_s1_suspends_account_while_preserving_records() -> None:
    """Block new operations while retaining records and policy access."""

    (
        suspend_account,
        authorize_activity,
        account_status,
        lifecycle_activity,
    ) = _account_suspension_contract()
    customer_account_id = "customer-account-1"

    def record(category: str) -> tuple[GovernedRecord, ...]:
        return (GovernedRecord(f"{category}-1", customer_account_id),)

    records = GovernedAccountRecords(
        reports=record("report"),
        validation_cycles=record("validation-cycle"),
        findings=record("finding"),
        credits=record("credit"),
        billing_records=record("billing-record"),
        audit_history=record("audit-record"),
    )
    account = GovernedCustomerAccount(
        customer_account_id=customer_account_id,
        status=account_status.ACTIVE,
        records=records,
    )
    original_records = account.records
    repository = CustomerAccountRepositorySpy()
    prior_audit_event = {
        "event_type": "account_created",
        "customer_account_id": customer_account_id,
        "actor_id": "human-user-owner",
    }
    audit_history = AccountAuditHistorySpy(events=[prior_audit_event])
    administrator_id = "administrator-1"

    suspended_account = suspend_account(
        administrator_id,
        account,
        repository,
        audit_history,
    )

    assert suspended_account.status is account_status.SUSPENDED
    assert suspended_account.records == original_records
    assert repository.saved_accounts == [suspended_account]

    policy = SuspensionPolicySpy()
    for actor_id in ("human-user-1", "software-client-1"):
        assert authorize_activity(
            suspended_account,
            actor_id,
            lifecycle_activity.OPEN_NEW_VALIDATION_CYCLE,
            policy,
        ) is False
    assert authorize_activity(
        suspended_account,
        "human-user-billing-administrator",
        lifecycle_activity.PURCHASE_RETAIL_CREDITS,
        policy,
    ) is False
    assert authorize_activity(
        suspended_account,
        "human-user-reviewer",
        lifecycle_activity.REVIEW_GOVERNED_RECORDS,
        policy,
    ) is True
    assert policy.evaluated_activities == [
        lifecycle_activity.REVIEW_GOVERNED_RECORDS
    ]
    assert audit_history.events == [
        prior_audit_event,
        {
            "event_type": "customer_account_suspended",
            "customer_account_id": customer_account_id,
            "actor_id": administrator_id,
        },
    ]
