"""Explicit customer-account membership invitation services."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Protocol

from app.services.customer_accounts import (
    CustomerAccountMembership,
    CustomerAccountRole,
)
from app.services.phone_numbers import normalize_phone_number


ALLOWED_PROPOSED_ROLES = frozenset(
    {"owner", "billing administrator", "validator", "reviewer"}
)


class MembershipInvitationStatus(StrEnum):
    """Lifecycle states established by implemented invitation rules."""

    PENDING = "pending"
    ACCEPTED = "accepted"


class InvitationAlreadyAcceptedError(ValueError):
    """Report an attempt to accept one invitation more than once."""


@dataclass(frozen=True)
class MembershipInvitation:
    """A no-access invitation awaiting explicit acceptance."""

    membership_invitation_id: str
    intended_human_user_id: str
    customer_account_id: str
    proposed_role: str
    internal_phone_number: str
    status: MembershipInvitationStatus
    grants_account_access: bool


class AccountMembership(Protocol):
    human_user_id: str
    role: CustomerAccountRole
    active: bool


class ActiveCustomerAccount(Protocol):
    customer_account_id: str
    active: bool
    memberships: tuple[AccountMembership, ...]


class HumanUser(Protocol):
    human_user_id: str


class HumanUserRepository(Protocol):
    def find_by_phone_number(
        self,
        internal_phone_number: str,
    ) -> HumanUser | None: ...


class MembershipInvitationIdGenerator(Protocol):
    def new_membership_invitation_id(self) -> str: ...


class MembershipInvitationRepository(Protocol):
    def add(self, invitation: MembershipInvitation) -> None: ...


class MembershipInvitationAcceptanceRepository(Protocol):
    def get_by_id(
        self,
        membership_invitation_id: str,
    ) -> MembershipInvitation | None: ...

    def save(self, invitation: MembershipInvitation) -> None: ...


class CustomerAccountMembershipRepository(Protocol):
    def add(self, membership: CustomerAccountMembership) -> None: ...


class AccountAuditHistory(Protocol):
    def record(self, **event: str) -> None: ...


def invite_person_to_customer_account(
    owner_human_user_id: str,
    customer_account: ActiveCustomerAccount,
    formatted_phone_number: str,
    proposed_role: str,
    human_user_repository: HumanUserRepository,
    invitation_id_generator: MembershipInvitationIdGenerator,
    invitation_repository: MembershipInvitationRepository,
    audit_history: AccountAuditHistory,
) -> MembershipInvitation:
    """Create a pending invitation without granting account membership."""

    owner_is_active = any(
        membership.human_user_id == owner_human_user_id
        and membership.role is CustomerAccountRole.OWNER
        and membership.active
        for membership in customer_account.memberships
    )
    if not customer_account.active or not owner_is_active:
        raise PermissionError(
            "An active customer-account owner must create the invitation."
        )
    if proposed_role not in ALLOWED_PROPOSED_ROLES:
        raise ValueError("The proposed customer-account role is not allowed.")

    internal_phone_number = normalize_phone_number(formatted_phone_number)
    intended_human_user = human_user_repository.find_by_phone_number(
        internal_phone_number
    )
    if intended_human_user is None:
        raise LookupError(
            "The invitation phone number does not identify a human user."
        )
    if any(
        membership.human_user_id == intended_human_user.human_user_id
        for membership in customer_account.memberships
    ):
        raise ValueError("The intended human user is already a member.")

    invitation = MembershipInvitation(
        membership_invitation_id=(
            invitation_id_generator.new_membership_invitation_id()
        ),
        intended_human_user_id=intended_human_user.human_user_id,
        customer_account_id=customer_account.customer_account_id,
        proposed_role=proposed_role,
        internal_phone_number=internal_phone_number,
        status=MembershipInvitationStatus.PENDING,
        grants_account_access=False,
    )
    invitation_repository.add(invitation)
    audit_history.record(
        event_type="membership_invitation_created",
        customer_account_id=customer_account.customer_account_id,
        actor_id=owner_human_user_id,
        subject_id=intended_human_user.human_user_id,
        membership_invitation_id=invitation.membership_invitation_id,
    )
    return invitation


def accept_membership_invitation(
    accepting_human_user_id: str,
    membership_invitation_id: str,
    invitation_repository: MembershipInvitationAcceptanceRepository,
    membership_repository: CustomerAccountMembershipRepository,
    audit_history: AccountAuditHistory,
) -> CustomerAccountMembership:
    """Accept one pending invitation and create one active membership."""

    invitation = invitation_repository.get_by_id(
        membership_invitation_id
    )
    if invitation is None:
        raise LookupError("The membership invitation does not exist.")
    if invitation.status is MembershipInvitationStatus.ACCEPTED:
        raise InvitationAlreadyAcceptedError(
            "The membership invitation has already been accepted."
        )
    if invitation.intended_human_user_id != accepting_human_user_id:
        raise PermissionError(
            "Only the intended human user can accept the invitation."
        )

    membership = CustomerAccountMembership(
        human_user_id=accepting_human_user_id,
        customer_account_id=invitation.customer_account_id,
        role=CustomerAccountRole(invitation.proposed_role),
        active=True,
    )
    membership_repository.add(membership)
    invitation_repository.save(
        replace(
            invitation,
            status=MembershipInvitationStatus.ACCEPTED,
        )
    )
    audit_history.record(
        event_type="membership_invitation_accepted",
        customer_account_id=invitation.customer_account_id,
        actor_id=accepting_human_user_id,
        subject_id=accepting_human_user_id,
        membership_invitation_id=invitation.membership_invitation_id,
    )
    return membership
