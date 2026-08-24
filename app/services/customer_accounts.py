"""Customer-account creation services."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol


class CustomerAccountRole(StrEnum):
    """Customer-account roles established by implemented business rules."""

    OWNER = "owner"


@dataclass(frozen=True)
class CustomerAccountMembership:
    """A human user's active role within one customer account."""

    human_user_id: str
    role: CustomerAccountRole
    active: bool


@dataclass(frozen=True)
class CustomerAccount:
    """Ownership and billing boundary with its initial membership."""

    customer_account_id: str
    is_ownership_boundary: bool
    is_billing_boundary: bool
    memberships: tuple[CustomerAccountMembership, ...]


class CustomerAccountApplicant(Protocol):
    """Verified, eligible human user creating an account."""

    human_user_id: str
    internal_phone_number: str
    phone_number_verified: bool
    eligible_to_create_customer_account: bool


class CustomerAccountIdGenerator(Protocol):
    """Boundary for issuing unique customer-account identifiers."""

    def new_customer_account_id(self) -> str: ...


class CustomerAccountRepository(Protocol):
    """Persistence boundary for customer-account aggregates."""

    def add(self, customer_account: CustomerAccount) -> None: ...


class AccountAuditHistory(Protocol):
    """Audit boundary for material customer-account events."""

    def record(self, **event: str) -> None: ...


def create_customer_account(
    person: CustomerAccountApplicant,
    id_generator: CustomerAccountIdGenerator,
    account_repository: CustomerAccountRepository,
    audit_history: AccountAuditHistory,
) -> CustomerAccount:
    """Create one account with the eligible person as its first owner."""

    customer_account_id = id_generator.new_customer_account_id()
    owner_membership = CustomerAccountMembership(
        human_user_id=person.human_user_id,
        role=CustomerAccountRole.OWNER,
        active=True,
    )
    customer_account = CustomerAccount(
        customer_account_id=customer_account_id,
        is_ownership_boundary=True,
        is_billing_boundary=True,
        memberships=(owner_membership,),
    )

    account_repository.add(customer_account)
    audit_history.record(
        event_type="customer_account_created",
        customer_account_id=customer_account_id,
        actor_id=person.human_user_id,
    )
    audit_history.record(
        event_type="owner_assigned",
        customer_account_id=customer_account_id,
        actor_id=person.human_user_id,
        subject_id=person.human_user_id,
    )
    return customer_account
