"""Customer-account-owned validation credit services."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Protocol

from app.services.account_authorization import (
    AuthorizationResult,
    CustomerAccountActivity,
    authorize_customer_activity,
)
from app.services.customer_accounts import CustomerAccountMembership


@dataclass(frozen=True)
class ValidationCreditLot:
    """A quantity of validation credits owned by one customer account."""

    validation_credit_lot_id: str
    customer_account_id: str
    payment_id: str
    remaining_quantity: int


class CompletedPayment(Protocol):
    payment_id: str
    customer_account_id: str
    status: str


class ValidationCreditIdGenerator(Protocol):
    def new_validation_credit_lot_id(self) -> str: ...


class ValidationCreditRepository(Protocol):
    def add(self, credit_lot: ValidationCreditLot) -> None: ...

    def save(self, credit_lot: ValidationCreditLot) -> None: ...


class CreditHistory(Protocol):
    def record(self, **event: object) -> None: ...


def issue_validation_credits(
    payment: CompletedPayment,
    purchaser: CustomerAccountMembership,
    quantity: int,
    id_generator: ValidationCreditIdGenerator,
    credit_repository: ValidationCreditRepository,
    credit_history: CreditHistory,
) -> ValidationCreditLot:
    """Issue a completed purchase to its customer account."""

    if payment.status != "completed":
        raise ValueError("Validation credits require a completed payment.")
    if quantity <= 0:
        raise ValueError("Validation credit quantity must be positive.")

    authorization = authorize_customer_activity(
        purchaser,
        payment.customer_account_id,
        CustomerAccountActivity.PURCHASE_VALIDATION_CREDITS,
    )
    if authorization.result is AuthorizationResult.DENIED:
        raise PermissionError(
            "Billing authority is required in the payment's account."
        )

    credit_lot = ValidationCreditLot(
        validation_credit_lot_id=(
            id_generator.new_validation_credit_lot_id()
        ),
        customer_account_id=payment.customer_account_id,
        payment_id=payment.payment_id,
        remaining_quantity=quantity,
    )
    credit_repository.add(credit_lot)
    credit_history.record(
        event_type="validation_credits_issued",
        customer_account_id=credit_lot.customer_account_id,
        actor_id=purchaser.human_user_id,
        payment_id=payment.payment_id,
        validation_credit_lot_id=credit_lot.validation_credit_lot_id,
        quantity=quantity,
    )
    return credit_lot


def consume_validation_credit(
    credit_lot: ValidationCreditLot,
    actor_id: str,
    credit_repository: ValidationCreditRepository,
    credit_history: CreditHistory,
) -> ValidationCreditLot:
    """Consume one account-owned credit and attribute the acting identity."""

    if credit_lot.remaining_quantity <= 0:
        raise ValueError("The validation credit lot is exhausted.")

    updated_credit_lot = replace(
        credit_lot,
        remaining_quantity=credit_lot.remaining_quantity - 1,
    )
    credit_repository.save(updated_credit_lot)
    credit_history.record(
        event_type="validation_credit_consumed",
        customer_account_id=credit_lot.customer_account_id,
        actor_id=actor_id,
        validation_credit_lot_id=credit_lot.validation_credit_lot_id,
        quantity=1,
    )
    return updated_credit_lot
