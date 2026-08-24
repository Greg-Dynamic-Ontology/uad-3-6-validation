"""Executable test for IT-15R1S2 invitation acceptance."""

from __future__ import annotations

from dataclasses import dataclass, field
from importlib import import_module
from typing import Any

import pytest

from app.services.account_invitations import (
    MembershipInvitation,
    MembershipInvitationStatus,
)
from app.services.customer_accounts import CustomerAccountRole


INVITATION_MODULE = "app.services.account_invitations"


@dataclass
class MembershipInvitationRepositorySpy:
    invitation: MembershipInvitation
    saved_invitations: list[MembershipInvitation] = field(default_factory=list)

    def get_by_id(
        self,
        membership_invitation_id: str,
    ) -> MembershipInvitation | None:
        if (
            self.invitation.membership_invitation_id
            == membership_invitation_id
        ):
            return self.invitation
        return None

    def save(self, invitation: MembershipInvitation) -> None:
        self.invitation = invitation
        self.saved_invitations.append(invitation)


@dataclass
class CustomerAccountMembershipRepositorySpy:
    added_memberships: list[object] = field(default_factory=list)

    def add(self, membership: object) -> None:
        self.added_memberships.append(membership)


@dataclass
class AccountAuditHistorySpy:
    events: list[dict[str, str]] = field(default_factory=list)

    def record(self, **event: str) -> None:
        self.events.append(event)


def _acceptance_contract() -> tuple[Any, type[Exception]]:
    """Load the acceptance contract expected by IT-15R1S2."""

    module = import_module(INVITATION_MODULE)
    accept_invitation = getattr(
        module,
        "accept_membership_invitation",
        None,
    )
    already_accepted_error = getattr(
        module,
        "InvitationAlreadyAcceptedError",
        None,
    )

    assert callable(accept_invitation), (
        "IT-15R1S2 requires accept_membership_invitation(...)."
    )
    assert hasattr(MembershipInvitationStatus, "ACCEPTED"), (
        "IT-15R1S2 requires MembershipInvitationStatus.ACCEPTED."
    )
    assert isinstance(already_accepted_error, type) and issubclass(
        already_accepted_error,
        Exception,
    ), "IT-15R1S2 requires InvitationAlreadyAcceptedError."
    assert hasattr(CustomerAccountRole, "VALIDATOR"), (
        "IT-15R1S2 requires CustomerAccountRole.VALIDATOR."
    )
    return accept_invitation, already_accepted_error


def test_it_15_r1_s2_accepts_invitation_exactly_once() -> None:
    """Create one active membership and audit one invitation acceptance."""

    accept_invitation, already_accepted_error = _acceptance_contract()
    human_user_id = "human-user-invitee"
    pending_invitation = MembershipInvitation(
        membership_invitation_id="membership-invitation-1",
        intended_human_user_id=human_user_id,
        customer_account_id="customer-account-1",
        proposed_role="validator",
        internal_phone_number="19999999976",
        status=MembershipInvitationStatus.PENDING,
        grants_account_access=False,
    )
    invitations = MembershipInvitationRepositorySpy(pending_invitation)
    memberships = CustomerAccountMembershipRepositorySpy()
    audit_history = AccountAuditHistorySpy()

    membership = accept_invitation(
        human_user_id,
        pending_invitation.membership_invitation_id,
        invitations,
        memberships,
        audit_history,
    )

    assert membership.human_user_id == human_user_id
    assert membership.customer_account_id == "customer-account-1"
    assert membership.role is CustomerAccountRole.VALIDATOR
    assert membership.active is True
    assert memberships.added_memberships == [membership]
    assert invitations.invitation.status is MembershipInvitationStatus.ACCEPTED
    assert len(invitations.saved_invitations) == 1
    assert audit_history.events == [
        {
            "event_type": "membership_invitation_accepted",
            "customer_account_id": "customer-account-1",
            "actor_id": human_user_id,
            "subject_id": human_user_id,
            "membership_invitation_id": "membership-invitation-1",
        }
    ]

    with pytest.raises(already_accepted_error):
        accept_invitation(
            human_user_id,
            pending_invitation.membership_invitation_id,
            invitations,
            memberships,
            audit_history,
        )

    assert memberships.added_memberships == [membership]
    assert len(invitations.saved_invitations) == 1
    assert len(audit_history.events) == 1
