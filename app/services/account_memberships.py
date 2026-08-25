"""Customer-account membership lifecycle services."""

from __future__ import annotations

from dataclasses import replace
from typing import Protocol

from app.services.customer_accounts import (
    CustomerAccountMembership,
    CustomerAccountRole,
)


class CustomerAccountMembershipRepository(Protocol):
    """Persistence boundary for customer-account memberships."""

    def save(self, membership: CustomerAccountMembership) -> None: ...


class AccountAuditHistory(Protocol):
    """Audit boundary for membership lifecycle events."""

    def record(self, **event: str) -> None: ...


def remove_customer_account_membership(
    owner_membership: CustomerAccountMembership,
    membership: CustomerAccountMembership,
    membership_repository: CustomerAccountMembershipRepository,
    audit_history: AccountAuditHistory,
) -> CustomerAccountMembership:
    """Deactivate one membership without changing customer-owned records."""

    owner_is_authorized = (
        owner_membership.active
        and owner_membership.role is CustomerAccountRole.OWNER
        and owner_membership.customer_account_id is not None
        and owner_membership.customer_account_id
        == membership.customer_account_id
    )
    if not owner_is_authorized:
        raise PermissionError(
            "An active owner in the same customer account is required."
        )

    removed_membership = replace(membership, active=False)
    membership_repository.save(removed_membership)
    audit_history.record(
        event_type="customer_account_membership_removed",
        customer_account_id=membership.customer_account_id,
        actor_id=owner_membership.human_user_id,
        subject_id=membership.human_user_id,
    )
    return removed_membership
