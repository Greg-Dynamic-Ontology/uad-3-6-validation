"""Customer-account membership lifecycle services."""

from __future__ import annotations

from dataclasses import replace
from typing import Protocol

from app.services.customer_accounts import (
    CustomerAccount,
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
    # Durable adapters need the acting identity to authorize the operation
    # against persisted memberships and attribute the same transaction.
    deactivate = getattr(membership_repository, "deactivate_membership", None)
    if callable(deactivate):
        deactivate(membership, actor_id=owner_membership.human_user_id)
    else:
        # Preserve the original save protocol for existing service callers.
        membership_repository.save(removed_membership)
    audit_history.record(
        event_type="customer_account_membership_removed",
        customer_account_id=membership.customer_account_id,
        actor_id=owner_membership.human_user_id,
        subject_id=membership.human_user_id,
    )
    return removed_membership


class CustomerAccountGrantRepository(Protocol):
    """Persistence boundary for an attributable membership grant."""

    def get(self, customer_account_id: str) -> CustomerAccount: ...

    def add_membership(
        self, membership: CustomerAccountMembership, *, actor_id: str,
    ) -> None: ...


def grant_customer_account_membership(
    *,
    actor_id: str,
    human_user_id: str,
    customer_account_id: str,
    role: CustomerAccountRole | str,
    account_repository: CustomerAccountGrantRepository,
    audit_history: AccountAuditHistory,
) -> CustomerAccountMembership:
    """Grant an explicit role in an existing active company account.

    The application supplies authenticated, linked UAD user IDs. Authentication
    and admission are prerequisites; this service does not infer membership
    from an email address or create a new account for the target user.
    """
    if not isinstance(actor_id, str) or not actor_id.strip():
        raise PermissionError("An identified acting UAD user is required.")
    if not isinstance(human_user_id, str) or not human_user_id.strip():
        raise ValueError("An identified target UAD user is required.")
    if not isinstance(customer_account_id, str) or not customer_account_id.strip():
        raise ValueError("An existing customer-account ID is required.")
    try:
        granted_role = CustomerAccountRole(role)
    except (TypeError, ValueError) as error:
        raise ValueError("Choose a supported customer-account role.") from error

    account = account_repository.get(customer_account_id)
    if account.customer_account_id != customer_account_id:
        raise ValueError("The repository returned a different customer account.")
    authorized = any(
        member.active
        and member.role == CustomerAccountRole.OWNER
        and member.human_user_id == actor_id
        and member.customer_account_id == customer_account_id
        for member in account.memberships
    )
    if not authorized:
        raise PermissionError("An active owner in the same customer account is required.")
    if account.status != "active" or account.account_type != "company":
        raise ValueError("Membership grants require an active company account.")
    if any(
        member.human_user_id == human_user_id
        and member.customer_account_id == customer_account_id
        and member.role == granted_role
        for member in account.memberships
    ):
        raise ValueError("This user already has that role; manage the existing membership.")

    membership = CustomerAccountMembership(
        human_user_id=human_user_id,
        customer_account_id=customer_account_id,
        role=granted_role,
        active=True,
    )
    # The adapter persists the membership and durable change attribution
    # together. Do not report success if persistence fails or is unconfirmed.
    account_repository.add_membership(membership, actor_id=actor_id)
    audit_history.record(
        event_type="customer_account_membership_granted",
        customer_account_id=customer_account_id,
        actor_id=actor_id,
        subject_id=human_user_id,
        role=granted_role.value,
    )
    return membership


class CustomerAccountRoleChangeRepository(Protocol):
    """Persistence boundary for an attributable role change."""

    def get(self, customer_account_id: str) -> CustomerAccount: ...

    def change_membership_role(
        self, membership: CustomerAccountMembership, *,
        role: CustomerAccountRole, actor_id: str,
    ) -> None: ...


def change_customer_account_membership_role(
    *,
    actor_id: str,
    membership: CustomerAccountMembership,
    role: CustomerAccountRole | str,
    account_repository: CustomerAccountRoleChangeRepository,
    audit_history: AccountAuditHistory,
) -> CustomerAccountMembership:
    """Change a stored role while preserving an active account owner."""
    if not isinstance(actor_id, str) or not actor_id.strip():
        raise PermissionError("An identified acting UAD user is required.")
    account_id = membership.customer_account_id
    if not isinstance(account_id, str) or not account_id.strip():
        raise ValueError("An existing customer-account ID is required.")
    try:
        new_role = CustomerAccountRole(role)
    except (TypeError, ValueError) as error:
        raise ValueError("Choose a supported customer-account role.") from error

    account = account_repository.get(account_id)
    if account.customer_account_id != account_id:
        raise ValueError("The repository returned a different customer account.")
    if not any(
        member.active and member.role == CustomerAccountRole.OWNER
        and member.human_user_id == actor_id
        and member.customer_account_id == account_id
        for member in account.memberships
    ):
        raise PermissionError("An active owner in the same customer account is required.")
    if account.status != "active" or account.account_type != "company":
        raise ValueError("Role changes require an active company account.")

    matches = [
        member for member in account.memberships
        if member.human_user_id == membership.human_user_id
        and member.customer_account_id == account_id
        and member.role == membership.role
    ]
    if len(matches) != 1:
        raise ValueError("The selected membership must identify exactly one stored role.")
    current = matches[0]
    if not current.active:
        raise ValueError("Only an active membership can change roles.")
    if new_role == current.role:
        return current
    if current.role == CustomerAccountRole.OWNER and not any(
        member.active and member.role == CustomerAccountRole.OWNER
        and member.customer_account_id == account_id
        and member.human_user_id != current.human_user_id
        for member in account.memberships
    ):
        raise ValueError("Another active owner must first be designated.")
    if any(
        member.human_user_id == current.human_user_id
        and member.customer_account_id == account_id
        and member.role == new_role
        for member in account.memberships
    ):
        raise ValueError("This user already has the requested role; manage that membership.")

    account_repository.change_membership_role(
        current, role=new_role, actor_id=actor_id,
    )
    updated = replace(current, role=new_role)
    audit_history.record(
        event_type="customer_account_membership_role_changed",
        customer_account_id=account_id,
        actor_id=actor_id,
        subject_id=current.human_user_id,
        previous_role=current.role.value,
        role=new_role.value,
    )
    return updated
