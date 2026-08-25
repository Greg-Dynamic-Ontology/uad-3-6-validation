"""Selection of one customer-account context for a human user."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.services.customer_accounts import CustomerAccountMembership


class AccountOwnedResource(Protocol):
    """A service resource owned by one customer account."""

    customer_account_id: str


class CustomerOwnedResources(Protocol):
    """Resource collections visible through an account context."""

    reports: tuple[AccountOwnedResource, ...]
    validation_cycles: tuple[AccountOwnedResource, ...]
    credits: tuple[AccountOwnedResource, ...]
    billing_records: tuple[AccountOwnedResource, ...]


@dataclass(frozen=True)
class CustomerAccountContext:
    """One active membership and its account-owned resource view."""

    customer_account_id: str
    membership: CustomerAccountMembership
    reports: tuple[AccountOwnedResource, ...]
    validation_cycles: tuple[AccountOwnedResource, ...]
    credits: tuple[AccountOwnedResource, ...]
    billing_records: tuple[AccountOwnedResource, ...]


def _owned_by(
    resources: tuple[AccountOwnedResource, ...],
    customer_account_id: str,
) -> tuple[AccountOwnedResource, ...]:
    return tuple(
        resource
        for resource in resources
        if resource.customer_account_id == customer_account_id
    )


def select_customer_account_context(
    human_user_id: str,
    customer_account_id: str,
    memberships: tuple[CustomerAccountMembership, ...],
    resources: CustomerOwnedResources,
) -> CustomerAccountContext:
    """Select an active membership and filter resources to its account."""

    membership = next(
        (
            candidate
            for candidate in memberships
            if candidate.human_user_id == human_user_id
            and candidate.customer_account_id == customer_account_id
            and candidate.active
        ),
        None,
    )
    if membership is None:
        raise PermissionError(
            "The human user has no active membership in this account."
        )

    return CustomerAccountContext(
        customer_account_id=customer_account_id,
        membership=membership,
        reports=_owned_by(resources.reports, customer_account_id),
        validation_cycles=_owned_by(
            resources.validation_cycles,
            customer_account_id,
        ),
        credits=_owned_by(resources.credits, customer_account_id),
        billing_records=_owned_by(
            resources.billing_records,
            customer_account_id,
        ),
    )
