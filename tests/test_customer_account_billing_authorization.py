"""Executable tests for IT-16R1S3 billing-administrator authority."""

from __future__ import annotations

from importlib import import_module
from typing import Any

import pytest

from app.services.customer_accounts import (
    CustomerAccountMembership,
    CustomerAccountRole,
)


AUTHORIZATION_MODULE = "app.services.account_authorization"
BILLING_ACTIVITY_NAMES = (
    "PURCHASE_VALIDATION_CREDITS",
    "VIEW_CREDIT_BALANCES_AND_LEDGER_ACTIVITY",
    "VIEW_PAYMENT_REFUND_AND_INVOICE_HISTORY",
)


def _billing_authorization_contract() -> tuple[Any, Any, Any]:
    """Load the billing authorization contract expected by IT-16R1S3."""

    module = import_module(AUTHORIZATION_MODULE)
    authorize = getattr(module, "authorize_customer_activity", None)
    activity = getattr(module, "CustomerAccountActivity", None)
    result = getattr(module, "AuthorizationResult", None)

    assert callable(authorize), (
        "IT-16R1S3 requires authorize_customer_activity(membership, "
        "customer_account_id, activity)."
    )
    assert activity is not None, (
        "IT-16R1S3 requires CustomerAccountActivity."
    )
    for activity_name in BILLING_ACTIVITY_NAMES:
        assert hasattr(activity, activity_name), (
            f"IT-16R1S3 requires CustomerAccountActivity.{activity_name}."
        )
    assert result is not None, "IT-16R1S3 requires AuthorizationResult."
    return authorize, activity, result


@pytest.mark.parametrize(
    "activity_name",
    BILLING_ACTIVITY_NAMES,
    ids=[
        "purchase-validation-credits",
        "view-credit-balances-and-ledger",
        "view-payment-refund-and-invoice-history",
    ],
)
def test_it_16_r1_s3_allows_billing_activity_only_within_member_account(
    activity_name: str,
) -> None:
    """Allow each billing capability here but deny it in another account."""

    authorize, activity, result = _billing_authorization_contract()
    member_account_id = "customer-account-1"
    billing_membership = CustomerAccountMembership(
        human_user_id="human-user-billing-administrator",
        customer_account_id=member_account_id,
        role=CustomerAccountRole.BILLING_ADMINISTRATOR,
        active=True,
    )
    requested_activity = getattr(activity, activity_name)

    member_account_decision = authorize(
        billing_membership,
        member_account_id,
        requested_activity,
    )
    other_account_decision = authorize(
        billing_membership,
        "customer-account-2",
        requested_activity,
    )

    assert member_account_decision.result is result.ALLOWED
    assert member_account_decision.customer_account_id == member_account_id
    assert other_account_decision.result is result.DENIED
    assert other_account_decision.customer_account_id == "customer-account-2"
