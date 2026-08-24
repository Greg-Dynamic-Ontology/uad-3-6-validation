"""Executable test for IT-15R1S1 explicit account invitations."""

from __future__ import annotations

from dataclasses import dataclass, field
from importlib import import_module
from typing import Any

import pytest

from app.services.customer_accounts import (
    CustomerAccountMembership,
    CustomerAccountRole,
)


INVITATION_MODULE = "app.services.account_invitations"


@dataclass(frozen=True)
class HumanUser:
    human_user_id: str
    internal_phone_number: str


@dataclass(frozen=True)
class ActiveCustomerAccount:
    customer_account_id: str
    active: bool
    memberships: tuple[CustomerAccountMembership, ...]


@dataclass
class HumanUserRepositorySpy:
    human_user: HumanUser
    lookup_calls: list[str] = field(default_factory=list)

    def find_by_phone_number(
        self,
        internal_phone_number: str,
    ) -> HumanUser | None:
        self.lookup_calls.append(internal_phone_number)
        if internal_phone_number == self.human_user.internal_phone_number:
            return self.human_user
        return None


@dataclass
class InvitationIdGeneratorStub:
    def new_membership_invitation_id(self) -> str:
        return "membership-invitation-1"


@dataclass
class MembershipInvitationRepositorySpy:
    added_invitations: list[object] = field(default_factory=list)

    def add(self, invitation: object) -> None:
        self.added_invitations.append(invitation)


@dataclass
class AccountAuditHistorySpy:
    events: list[dict[str, str]] = field(default_factory=list)

    def record(self, **event: str) -> None:
        self.events.append(event)


def _invitation_contract() -> tuple[Any, Any]:
    """Load the invitation contract expected by IT-15R1S1."""

    try:
        module = import_module(INVITATION_MODULE)
    except ModuleNotFoundError as error:
        if error.name != INVITATION_MODULE:
            raise
        pytest.fail(
            "IT-15R1S1 requires app.services.account_invitations before "
            "explicit membership invitations can become green.",
            pytrace=False,
        )

    invite_person = getattr(
        module,
        "invite_person_to_customer_account",
        None,
    )
    invitation_status = getattr(
        module,
        "MembershipInvitationStatus",
        None,
    )
    assert callable(invite_person), (
        "IT-15R1S1 requires invite_person_to_customer_account(...)."
    )
    assert invitation_status is not None and hasattr(
        invitation_status,
        "PENDING",
    ), "IT-15R1S1 requires MembershipInvitationStatus.PENDING."
    return invite_person, invitation_status


def test_it_15_r1_s1_owner_invites_user_with_pending_no_access_status() -> None:
    """Create and audit an explicit invitation without granting membership."""

    invite_person, invitation_status = _invitation_contract()
    owner = HumanUser("human-user-owner", "19999999999")
    intended_human_user = HumanUser("human-user-invitee", "19999999976")
    owner_membership = CustomerAccountMembership(
        human_user_id=owner.human_user_id,
        role=CustomerAccountRole.OWNER,
        active=True,
    )
    customer_account = ActiveCustomerAccount(
        customer_account_id="customer-account-1",
        active=True,
        memberships=(owner_membership,),
    )
    human_users = HumanUserRepositorySpy(intended_human_user)
    invitations = MembershipInvitationRepositorySpy()
    audit_history = AccountAuditHistorySpy()

    invitation = invite_person(
        owner.human_user_id,
        customer_account,
        "+1-999-999-9976",
        "validator",
        human_users,
        InvitationIdGeneratorStub(),
        invitations,
        audit_history,
    )

    assert invitation.membership_invitation_id == "membership-invitation-1"
    assert invitation.status is invitation_status.PENDING
    assert invitation.intended_human_user_id == intended_human_user.human_user_id
    assert invitation.customer_account_id == customer_account.customer_account_id
    assert invitation.proposed_role == "validator"
    assert invitation.internal_phone_number == "19999999976"
    assert len(invitation.internal_phone_number) == 11
    assert set(invitation.internal_phone_number) <= set("0123456789")
    assert invitation.grants_account_access is False
    assert invitations.added_invitations == [invitation]

    assert all(
        membership.human_user_id != intended_human_user.human_user_id
        for membership in customer_account.memberships
    )
    assert human_users.lookup_calls == ["19999999976"]
    assert audit_history.events == [
        {
            "event_type": "membership_invitation_created",
            "customer_account_id": "customer-account-1",
            "actor_id": owner.human_user_id,
            "subject_id": intended_human_user.human_user_id,
            "membership_invitation_id": "membership-invitation-1",
        }
    ]
