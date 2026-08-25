"""Executable tests for IT-16R1S2 owner-only account management."""

from __future__ import annotations

from dataclasses import dataclass, field
from importlib import import_module
from typing import Any

import pytest

from app.services.customer_accounts import (
    CustomerAccountMembership,
    CustomerAccountRole,
)


AUTHORIZATION_MODULE = "app.services.account_authorization"


@dataclass(frozen=True)
class ActiveCustomerAccount:
    customer_account_id: str
    active: bool
    memberships: tuple[CustomerAccountMembership, ...]


@dataclass
class AccountAuditHistorySpy:
    events: list[dict[str, str]] = field(default_factory=list)

    def record(self, **event: str) -> None:
        self.events.append(event)


def _owner_authorization_contract() -> tuple[Any, Any, Any]:
    """Load the protected-action contract expected by IT-16R1S2."""

    module = import_module(AUTHORIZATION_MODULE)
    request_activity = getattr(
        module,
        "request_customer_account_activity",
        None,
    )
    activity = getattr(module, "CustomerAccountActivity", None)
    result = getattr(module, "AuthorizationResult", None)

    assert callable(request_activity), (
        "IT-16R1S2 requires request_customer_account_activity(membership, "
        "customer_account, activity, audit_history)."
    )
    assert activity is not None, (
        "IT-16R1S2 requires CustomerAccountActivity."
    )
    assert result is not None, "IT-16R1S2 requires AuthorizationResult."
    return request_activity, activity, result


@pytest.mark.parametrize(
    ("role", "activity_name"),
    [
        (
            CustomerAccountRole.BILLING_ADMINISTRATOR,
            "MANAGE_MEMBERSHIP_AND_ACCOUNT_CLOSURE",
        ),
        (
            CustomerAccountRole.VALIDATOR,
            "CLOSE_CUSTOMER_ACCOUNT",
        ),
    ],
    ids=[
        "non-owner-cannot-manage-membership",
        "non-owner-cannot-close-account",
    ],
)
def test_it_16_r1_s2_requires_owner_for_membership_and_account_closure(
    role: CustomerAccountRole,
    activity_name: str,
) -> None:
    """Deny, preserve, and audit each non-owner protected request."""

    request_activity, activity, result = _owner_authorization_contract()
    customer_account_id = "customer-account-1"
    membership = CustomerAccountMembership(
        human_user_id="human-user-1",
        customer_account_id=customer_account_id,
        role=role,
        active=True,
    )
    customer_account = ActiveCustomerAccount(
        customer_account_id=customer_account_id,
        active=True,
        memberships=(membership,),
    )
    original_account_state = (
        customer_account.active,
        customer_account.memberships,
    )
    audit_history = AccountAuditHistorySpy()
    requested_activity = getattr(activity, activity_name)

    decision = request_activity(
        membership,
        customer_account,
        requested_activity,
        audit_history,
    )

    assert decision.result is result.DENIED
    assert decision.customer_account_id == customer_account_id
    assert (
        customer_account.active,
        customer_account.memberships,
    ) == original_account_state
    assert audit_history.events == [
        {
            "event_type": "customer_account_activity_denied",
            "customer_account_id": customer_account_id,
            "actor_id": membership.human_user_id,
            "activity": requested_activity.value,
        }
    ]
