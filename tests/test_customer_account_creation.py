"""Executable test for IT-14R1S1 customer-account creation."""

from __future__ import annotations

from dataclasses import dataclass, field
from importlib import import_module
from typing import Any

import pytest


CUSTOMER_ACCOUNT_MODULE = "app.services.customer_accounts"


@dataclass(frozen=True)
class VerifiedEligiblePerson:
    """Human user satisfying the scenario's account-creation preconditions."""

    human_user_id: str
    internal_phone_number: str
    phone_number_verified: bool = True
    eligible_to_create_customer_account: bool = True


@dataclass
class CustomerAccountIdGeneratorSpy:
    """Return one deterministic unique ID and record issuance."""

    identifier: str
    issuance_count: int = 0

    def new_customer_account_id(self) -> str:
        self.issuance_count += 1
        return self.identifier


@dataclass
class CustomerAccountRepositorySpy:
    """Record newly persisted customer-account aggregates."""

    added_accounts: list[object] = field(default_factory=list)

    def add(self, customer_account: object) -> None:
        self.added_accounts.append(customer_account)


@dataclass
class AccountAuditHistorySpy:
    """Record material account events in their accepted order."""

    events: list[dict[str, str]] = field(default_factory=list)

    def record(self, **event: str) -> None:
        self.events.append(event)


def _account_creation_contract() -> tuple[Any, Any]:
    """Load the customer-account contract expected by IT-14R1S1."""

    try:
        module = import_module(CUSTOMER_ACCOUNT_MODULE)
    except ModuleNotFoundError as error:
        if error.name != CUSTOMER_ACCOUNT_MODULE:
            raise
        pytest.fail(
            "IT-14R1S1 requires app.services.customer_accounts before "
            "customer-account creation can become green.",
            pytrace=False,
        )

    create_customer_account = getattr(
        module,
        "create_customer_account",
        None,
    )
    customer_account_role = getattr(
        module,
        "CustomerAccountRole",
        None,
    )

    assert callable(create_customer_account), (
        "IT-14R1S1 requires create_customer_account(person, id_generator, "
        "account_repository, audit_history)."
    )
    assert customer_account_role is not None and hasattr(
        customer_account_role,
        "OWNER",
    ), "IT-14R1S1 requires CustomerAccountRole.OWNER."
    return create_customer_account, customer_account_role


def test_it_14_r1_s1_creates_customer_account_with_first_owner() -> None:
    """Create one account boundary, active owner, and auditable history."""

    create_customer_account, customer_account_role = (
        _account_creation_contract()
    )
    person = VerifiedEligiblePerson(
        human_user_id="human-user-1",
        internal_phone_number="19999999999",
    )
    id_generator = CustomerAccountIdGeneratorSpy("customer-account-1")
    repository = CustomerAccountRepositorySpy()
    audit_history = AccountAuditHistorySpy()

    customer_account = create_customer_account(
        person,
        id_generator,
        repository,
        audit_history,
    )

    assert customer_account.customer_account_id == "customer-account-1"
    assert id_generator.issuance_count == 1
    assert customer_account.is_ownership_boundary is True
    assert customer_account.is_billing_boundary is True
    assert repository.added_accounts == [customer_account]

    assert len(customer_account.memberships) == 1
    first_membership = customer_account.memberships[0]
    assert first_membership.human_user_id == person.human_user_id
    assert first_membership.role is customer_account_role.OWNER
    assert first_membership.active is True

    assert audit_history.events == [
        {
            "event_type": "customer_account_created",
            "customer_account_id": "customer-account-1",
            "actor_id": person.human_user_id,
        },
        {
            "event_type": "owner_assigned",
            "customer_account_id": "customer-account-1",
            "actor_id": person.human_user_id,
            "subject_id": person.human_user_id,
        },
    ]
