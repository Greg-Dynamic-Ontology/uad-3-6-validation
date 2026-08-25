"""Executable tests for IT-19R1S1 customer-account isolation."""

from __future__ import annotations

from dataclasses import dataclass, field
from importlib import import_module
from typing import Any

import pytest

from app.services.customer_accounts import (
    CustomerAccountMembership,
    CustomerAccountRole,
)


RESOURCE_ACCESS_MODULE = "app.services.account_resource_access"


@dataclass(frozen=True)
class ProtectedAccountResource:
    resource_id: str
    resource_type: str
    customer_account_id: str
    protected_value: str


@dataclass
class SecurityReviewHistorySpy:
    events: list[dict[str, str]] = field(default_factory=list)

    def record(self, **event: str) -> None:
        self.events.append(event)


def _resource_access_contract() -> tuple[Any, Any]:
    """Load the protected-resource contract expected by IT-19R1S1."""

    try:
        module = import_module(RESOURCE_ACCESS_MODULE)
    except ModuleNotFoundError as error:
        if error.name != RESOURCE_ACCESS_MODULE:
            raise
        pytest.fail(
            "IT-19R1S1 requires app.services.account_resource_access "
            "before cross-account isolation can become green.",
            pytrace=False,
        )

    request_resource = getattr(
        module,
        "request_customer_account_resource",
        None,
    )
    access_result = getattr(module, "ResourceAccessResult", None)
    assert callable(request_resource), (
        "IT-19R1S1 requires request_customer_account_resource("
        "membership, resource, security_review_history)."
    )
    assert access_result is not None and hasattr(access_result, "DENIED"), (
        "IT-19R1S1 requires ResourceAccessResult.DENIED."
    )
    return request_resource, access_result


@pytest.mark.parametrize(
    "resource_type",
    [
        "report",
        "validation cycle",
        "finding",
        "credit entry",
        "billing record",
    ],
    ids=[
        "report",
        "validation-cycle",
        "finding",
        "credit-entry",
        "billing-record",
    ],
)
def test_it_19_r1_s1_isolates_one_customer_account_from_another(
    resource_type: str,
) -> None:
    """Deny disclosure, preserve the record, and audit cross-account access."""

    request_resource, access_result = _resource_access_contract()
    protected_account_id = "customer-account-protected"
    actor_account_id = "customer-account-requesting"
    actor = CustomerAccountMembership(
        human_user_id="human-user-requesting",
        customer_account_id=actor_account_id,
        role=CustomerAccountRole.OWNER,
        active=True,
    )
    resource = ProtectedAccountResource(
        resource_id=f"{resource_type.replace(' ', '-')}-1",
        resource_type=resource_type,
        customer_account_id=protected_account_id,
        protected_value="must-not-be-disclosed",
    )
    original_resource = resource
    security_review_history = SecurityReviewHistorySpy()

    decision = request_resource(
        actor,
        resource,
        security_review_history,
    )

    assert decision.result is access_result.DENIED
    assert decision.resource is None
    assert resource == original_resource
    assert security_review_history.events == [
        {
            "event_type": "cross_account_resource_access_denied",
            "actor_customer_account_id": actor_account_id,
            "protected_customer_account_id": protected_account_id,
            "actor_id": actor.human_user_id,
            "resource_type": resource_type,
            "resource_id": resource.resource_id,
        }
    ]
