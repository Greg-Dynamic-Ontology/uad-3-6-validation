"""Executable test for IT-18R1S1 customer-owned validation credits."""

from __future__ import annotations

from dataclasses import dataclass, field
from importlib import import_module
from typing import Any

import pytest

from app.services.account_memberships import (
    remove_customer_account_membership,
)
from app.services.customer_accounts import (
    CustomerAccountMembership,
    CustomerAccountRole,
)


VALIDATION_CREDITS_MODULE = "app.services.validation_credits"


@dataclass(frozen=True)
class CompletedPayment:
    payment_id: str
    customer_account_id: str
    status: str = "completed"


@dataclass
class ValidationCreditIdGeneratorStub:
    def new_validation_credit_lot_id(self) -> str:
        return "validation-credit-lot-1"


@dataclass
class ValidationCreditRepositorySpy:
    credit_lots: list[object] = field(default_factory=list)

    def add(self, credit_lot: object) -> None:
        self.credit_lots.append(credit_lot)

    def save(self, credit_lot: object) -> None:
        self.credit_lots = [credit_lot]


@dataclass
class MembershipRepositorySpy:
    saved_memberships: list[CustomerAccountMembership] = field(
        default_factory=list
    )

    def save(self, membership: CustomerAccountMembership) -> None:
        self.saved_memberships.append(membership)


@dataclass
class EventHistorySpy:
    events: list[dict[str, object]] = field(default_factory=list)

    def record(self, **event: object) -> None:
        self.events.append(event)


def _validation_credit_contract() -> tuple[Any, Any]:
    """Load the validation-credit contract expected by IT-18R1S1."""

    try:
        module = import_module(VALIDATION_CREDITS_MODULE)
    except ModuleNotFoundError as error:
        if error.name != VALIDATION_CREDITS_MODULE:
            raise
        pytest.fail(
            "IT-18R1S1 requires app.services.validation_credits before "
            "customer-owned credits can become green.",
            pytrace=False,
        )

    issue_credits = getattr(module, "issue_validation_credits", None)
    consume_credit = getattr(module, "consume_validation_credit", None)
    assert callable(issue_credits), (
        "IT-18R1S1 requires issue_validation_credits(payment, purchaser, "
        "quantity, id_generator, credit_repository, credit_history)."
    )
    assert callable(consume_credit), (
        "IT-18R1S1 requires consume_validation_credit(credit_lot, "
        "actor_id, credit_repository, credit_history)."
    )
    return issue_credits, consume_credit


def test_it_18_r1_s1_makes_validation_credits_customer_owned() -> None:
    """Retain account ownership while attributing purchase and use actors."""

    issue_credits, consume_credit = _validation_credit_contract()
    customer_account_id = "customer-account-1"
    owner = CustomerAccountMembership(
        human_user_id="human-user-owner",
        customer_account_id=customer_account_id,
        role=CustomerAccountRole.OWNER,
        active=True,
    )
    purchaser = CustomerAccountMembership(
        human_user_id="human-user-billing-administrator",
        customer_account_id=customer_account_id,
        role=CustomerAccountRole.BILLING_ADMINISTRATOR,
        active=True,
    )
    payment = CompletedPayment("payment-1", customer_account_id)
    credits = ValidationCreditRepositorySpy()
    credit_history = EventHistorySpy()

    credit_lot = issue_credits(
        payment,
        purchaser,
        3,
        ValidationCreditIdGeneratorStub(),
        credits,
        credit_history,
    )

    assert credit_lot.validation_credit_lot_id == "validation-credit-lot-1"
    assert credit_lot.customer_account_id == customer_account_id
    assert credit_lot.remaining_quantity == 3
    assert not hasattr(credit_lot, "owner_human_user_id")
    assert credits.credit_lots == [credit_lot]

    remove_customer_account_membership(
        owner,
        purchaser,
        MembershipRepositorySpy(),
        EventHistorySpy(),
    )
    assert credits.credit_lots == [credit_lot]

    acting_software_client_id = "software-client-1"
    updated_credit_lot = consume_credit(
        credit_lot,
        acting_software_client_id,
        credits,
        credit_history,
    )

    assert updated_credit_lot.customer_account_id == customer_account_id
    assert updated_credit_lot.remaining_quantity == 2
    assert credit_history.events == [
        {
            "event_type": "validation_credits_issued",
            "customer_account_id": customer_account_id,
            "actor_id": purchaser.human_user_id,
            "payment_id": payment.payment_id,
            "validation_credit_lot_id": "validation-credit-lot-1",
            "quantity": 3,
        },
        {
            "event_type": "validation_credit_consumed",
            "customer_account_id": customer_account_id,
            "actor_id": acting_software_client_id,
            "validation_credit_lot_id": "validation-credit-lot-1",
            "quantity": 1,
        },
    ]
