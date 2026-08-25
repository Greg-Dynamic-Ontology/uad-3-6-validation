"""Access control for resources protected by a customer-account boundary."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from app.services.customer_accounts import CustomerAccountMembership


class ProtectedAccountResource(Protocol):
    resource_id: str
    resource_type: str
    customer_account_id: str


class SecurityReviewHistory(Protocol):
    def record(self, **event: str) -> None: ...


class ResourceAccessResult(StrEnum):
    """Possible protected-resource access outcomes."""

    ALLOWED = "allowed"
    DENIED = "denied"


@dataclass(frozen=True)
class CustomerAccountResourceAccessDecision:
    """An access result that discloses a resource only when authorized."""

    result: ResourceAccessResult
    resource: ProtectedAccountResource | None


def request_customer_account_resource(
    membership: CustomerAccountMembership,
    resource: ProtectedAccountResource,
    security_review_history: SecurityReviewHistory,
) -> CustomerAccountResourceAccessDecision:
    """Return a protected resource only within its active account context."""

    is_allowed = (
        membership.active
        and membership.customer_account_id == resource.customer_account_id
    )
    if is_allowed:
        return CustomerAccountResourceAccessDecision(
            result=ResourceAccessResult.ALLOWED,
            resource=resource,
        )

    is_cross_account = (
        membership.customer_account_id != resource.customer_account_id
    )
    security_review_history.record(
        event_type=(
            "cross_account_resource_access_denied"
            if is_cross_account
            else "inactive_membership_resource_access_denied"
        ),
        actor_customer_account_id=membership.customer_account_id or "",
        protected_customer_account_id=resource.customer_account_id,
        actor_id=membership.human_user_id,
        resource_type=resource.resource_type,
        resource_id=resource.resource_id,
    )
    return CustomerAccountResourceAccessDecision(
        result=ResourceAccessResult.DENIED,
        resource=None,
    )
