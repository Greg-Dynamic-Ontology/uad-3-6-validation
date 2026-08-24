"""Executable test for IT-14R1S2 solo-appraiser registration."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.services.customer_accounts import (
    CustomerAccount,
    CustomerAccountRole,
    create_customer_account,
)


@dataclass(frozen=True)
class SoloAppraiser:
    """Verified solo appraiser eligible to create a customer account."""

    human_user_id: str = "solo-appraiser-1"
    internal_phone_number: str = "19999999999"
    phone_number_verified: bool = True
    eligible_to_create_customer_account: bool = True


@dataclass
class CustomerAccountIdGeneratorStub:
    """Issue the account identifier used by this executable example."""

    def new_customer_account_id(self) -> str:
        return "customer-account-solo-1"


@dataclass
class CustomerAccountRepositorySpy:
    """Record persisted accounts."""

    added_accounts: list[CustomerAccount] = field(default_factory=list)

    def add(self, customer_account: CustomerAccount) -> None:
        self.added_accounts.append(customer_account)


@dataclass
class AccountAuditHistorySpy:
    """Record the shared customer-account audit history."""

    events: list[dict[str, str]] = field(default_factory=list)

    def record(self, **event: str) -> None:
        self.events.append(event)


def test_it_14_r1_s2_represents_solo_appraiser_as_one_user_account() -> None:
    """Use the ordinary customer-account model for a solo appraiser."""

    solo_appraiser = SoloAppraiser()
    repository = CustomerAccountRepositorySpy()
    audit_history = AccountAuditHistorySpy()

    customer_account = create_customer_account(
        solo_appraiser,
        CustomerAccountIdGeneratorStub(),
        repository,
        audit_history,
    )

    assert type(customer_account) is CustomerAccount
    assert customer_account.customer_account_id == "customer-account-solo-1"
    assert customer_account.is_ownership_boundary is True
    assert customer_account.is_billing_boundary is True
    assert repository.added_accounts == [customer_account]

    assert len(customer_account.memberships) == 1
    membership = customer_account.memberships[0]
    assert membership.human_user_id == solo_appraiser.human_user_id
    assert membership.role is CustomerAccountRole.OWNER
    assert membership.active is True

    assert [event["event_type"] for event in audit_history.events] == [
        "customer_account_created",
        "owner_assigned",
    ]
