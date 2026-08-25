"""Executable tests for IT-16R1S1 role-based authorization."""

from __future__ import annotations

from importlib import import_module
from typing import Any

import pytest

from app.services.customer_accounts import (
    CustomerAccountMembership,
    CustomerAccountRole,
)


AUTHORIZATION_MODULE = "app.services.account_authorization"


def _authorization_contract() -> tuple[Any, Any, Any]:
    """Load the authorization contract expected by IT-16R1S1."""

    try:
        module = import_module(AUTHORIZATION_MODULE)
    except ModuleNotFoundError as error:
        if error.name != AUTHORIZATION_MODULE:
            raise
        pytest.fail(
            "IT-16R1S1 requires app.services.account_authorization before "
            "role-based decisions can become green.",
            pytrace=False,
        )

    authorize = getattr(module, "authorize_customer_activity", None)
    activity = getattr(module, "CustomerAccountActivity", None)
    result = getattr(module, "AuthorizationResult", None)

    assert callable(authorize), (
        "IT-16R1S1 requires authorize_customer_activity(membership, "
        "customer_account_id, activity)."
    )
    assert activity is not None, (
        "IT-16R1S1 requires CustomerAccountActivity."
    )
    assert result is not None, "IT-16R1S1 requires AuthorizationResult."
    return authorize, activity, result


@pytest.mark.parametrize(
    ("role", "activity_name", "expected_result_name"),
    [
        (
            CustomerAccountRole.OWNER,
            "MANAGE_MEMBERSHIP_AND_ACCOUNT_CLOSURE",
            "ALLOWED",
        ),
        (
            CustomerAccountRole.BILLING_ADMINISTRATOR,
            "PURCHASE_CREDITS_AND_VIEW_FINANCIAL_HISTORY",
            "ALLOWED",
        ),
        (
            CustomerAccountRole.VALIDATOR,
            "SUBMIT_REPORTS_AND_MANAGE_VALIDATION_CYCLES",
            "ALLOWED",
        ),
        (
            CustomerAccountRole.REVIEWER,
            "VIEW_REPORTS_FINDINGS_AND_CYCLE_HISTORIES",
            "ALLOWED",
        ),
        (
            CustomerAccountRole.REVIEWER,
            "SUBMIT_REPORT_FOR_NEW_VALIDATION_CYCLE",
            "DENIED",
        ),
        (
            CustomerAccountRole.VALIDATOR,
            "CLOSE_CUSTOMER_ACCOUNT",
            "DENIED",
        ),
    ],
    ids=[
        "owner-manages-membership-and-closure",
        "billing-administrator-manages-finances",
        "validator-manages-validation",
        "reviewer-views-validation-history",
        "reviewer-cannot-submit-report",
        "validator-cannot-close-account",
    ],
)
def test_it_16_r1_s1_authorizes_activity_by_role_within_account(
    role: CustomerAccountRole,
    activity_name: str,
    expected_result_name: str,
) -> None:
    """Evaluate every outlined role/activity pair in one account scope."""

    authorize, activity, result = _authorization_contract()
    customer_account_id = "customer-account-1"
    membership = CustomerAccountMembership(
        human_user_id="human-user-1",
        customer_account_id=customer_account_id,
        role=role,
        active=True,
    )

    decision = authorize(
        membership,
        customer_account_id,
        getattr(activity, activity_name),
    )

    assert decision.result is getattr(result, expected_result_name)
    assert decision.customer_account_id == customer_account_id
