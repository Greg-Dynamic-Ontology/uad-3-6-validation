"""Executable test for IT-17R1S1 membership removal retention."""

from __future__ import annotations

from dataclasses import dataclass, field
from importlib import import_module
from typing import Any

import pytest

from app.services.account_authorization import (
    AuthorizationResult,
    CustomerAccountActivity,
    authorize_customer_activity,
)
from app.services.customer_accounts import (
    CustomerAccountMembership,
    CustomerAccountRole,
)


ACCOUNT_MEMBERSHIP_MODULE = "app.services.account_memberships"


@dataclass(frozen=True)
class AccountOwnedRecord:
    record_id: str
    customer_account_id: str


@dataclass(frozen=True)
class AttributedAccountAction:
    action_id: str
    customer_account_id: str
    actor_id: str


@dataclass(frozen=True)
class CustomerAccountRecords:
    reports: tuple[AccountOwnedRecord, ...]
    validation_cycles: tuple[AccountOwnedRecord, ...]
    credits: tuple[AccountOwnedRecord, ...]
    billing_records: tuple[AccountOwnedRecord, ...]
    prior_actions: tuple[AttributedAccountAction, ...]


@dataclass
class MembershipRepositorySpy:
    saved_memberships: list[CustomerAccountMembership] = field(
        default_factory=list
    )

    def save(self, membership: CustomerAccountMembership) -> None:
        self.saved_memberships.append(membership)


@dataclass
class AccountAuditHistorySpy:
    events: list[dict[str, str]]

    def record(self, **event: str) -> None:
        self.events.append(event)


def _membership_removal_contract() -> Any:
    """Load the membership-removal contract expected by IT-17R1S1."""

    try:
        module = import_module(ACCOUNT_MEMBERSHIP_MODULE)
    except ModuleNotFoundError as error:
        if error.name != ACCOUNT_MEMBERSHIP_MODULE:
            raise
        pytest.fail(
            "IT-17R1S1 requires app.services.account_memberships before "
            "membership removal can become green.",
            pytrace=False,
        )

    remove_membership = getattr(
        module,
        "remove_customer_account_membership",
        None,
    )
    assert callable(remove_membership), (
        "IT-17R1S1 requires remove_customer_account_membership("
        "owner_membership, membership, membership_repository, "
        "audit_history)."
    )
    return remove_membership


def test_it_17_r1_s1_removes_member_without_removing_account_records() -> None:
    """Deactivate access while retaining ownership and attribution."""

    remove_membership = _membership_removal_contract()
    customer_account_id = "customer-account-1"
    owner = CustomerAccountMembership(
        human_user_id="human-user-owner",
        customer_account_id=customer_account_id,
        role=CustomerAccountRole.OWNER,
        active=True,
    )
    member = CustomerAccountMembership(
        human_user_id="human-user-validator",
        customer_account_id=customer_account_id,
        role=CustomerAccountRole.VALIDATOR,
        active=True,
    )
    records = CustomerAccountRecords(
        reports=(AccountOwnedRecord("report-1", customer_account_id),),
        validation_cycles=(
            AccountOwnedRecord("validation-cycle-1", customer_account_id),
        ),
        credits=(AccountOwnedRecord("credit-lot-1", customer_account_id),),
        billing_records=(
            AccountOwnedRecord("invoice-1", customer_account_id),
        ),
        prior_actions=(
            AttributedAccountAction(
                "action-1",
                customer_account_id,
                member.human_user_id,
            ),
        ),
    )
    original_records = records
    memberships = MembershipRepositorySpy()
    prior_audit_event = {
        "event_type": "report_submitted",
        "customer_account_id": customer_account_id,
        "actor_id": member.human_user_id,
    }
    audit_history = AccountAuditHistorySpy(events=[prior_audit_event])

    removed_membership = remove_membership(
        owner,
        member,
        memberships,
        audit_history,
    )

    assert removed_membership.active is False
    assert removed_membership.customer_account_id == customer_account_id
    assert removed_membership.human_user_id == member.human_user_id
    assert memberships.saved_memberships == [removed_membership]

    authorization = authorize_customer_activity(
        removed_membership,
        customer_account_id,
        CustomerAccountActivity.SUBMIT_REPORTS_AND_MANAGE_VALIDATION_CYCLES,
    )
    assert authorization.result is AuthorizationResult.DENIED

    assert records == original_records
    account_owned_records = (
        records.reports
        + records.validation_cycles
        + records.credits
        + records.billing_records
    )
    assert all(
        record.customer_account_id == customer_account_id
        for record in account_owned_records
    )
    assert records.prior_actions[0].actor_id == member.human_user_id
    assert audit_history.events == [
        prior_audit_event,
        {
            "event_type": "customer_account_membership_removed",
            "customer_account_id": customer_account_id,
            "actor_id": owner.human_user_id,
            "subject_id": member.human_user_id,
        },
    ]
