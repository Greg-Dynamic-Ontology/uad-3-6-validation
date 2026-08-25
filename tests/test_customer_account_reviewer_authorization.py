"""Executable tests for IT-16R1S5 read-only reviewer authority."""

from __future__ import annotations

from importlib import import_module
from typing import Any

import pytest

from app.services.customer_accounts import (
    CustomerAccountMembership,
    CustomerAccountRole,
)


AUTHORIZATION_MODULE = "app.services.account_authorization"


def _reviewer_authorization_contract() -> tuple[Any, Any, Any]:
    """Load the reviewer authorization contract expected by IT-16R1S5."""

    module = import_module(AUTHORIZATION_MODULE)
    authorize = getattr(module, "authorize_customer_activity", None)
    activity = getattr(module, "CustomerAccountActivity", None)
    result = getattr(module, "AuthorizationResult", None)

    assert callable(authorize), (
        "IT-16R1S5 requires authorize_customer_activity(membership, "
        "customer_account_id, activity)."
    )
    assert activity is not None, (
        "IT-16R1S5 requires CustomerAccountActivity."
    )
    assert result is not None, "IT-16R1S5 requires AuthorizationResult."
    return authorize, activity, result


def _active_reviewer() -> CustomerAccountMembership:
    return CustomerAccountMembership(
        human_user_id="human-user-reviewer",
        customer_account_id="customer-account-1",
        role=CustomerAccountRole.REVIEWER,
        active=True,
    )


def test_it_16_r1_s5_allows_reviewer_reads_only_in_authorized_account() -> None:
    """Allow reviewer information access without crossing account scope."""

    authorize, activity, result = _reviewer_authorization_contract()
    reviewer = _active_reviewer()
    read_activity = activity.VIEW_REPORTS_FINDINGS_AND_CYCLE_HISTORIES

    own_account_decision = authorize(
        reviewer,
        "customer-account-1",
        read_activity,
    )
    other_account_decision = authorize(
        reviewer,
        "customer-account-2",
        read_activity,
    )

    assert own_account_decision.result is result.ALLOWED
    assert other_account_decision.result is result.DENIED


@pytest.mark.parametrize(
    "activity_name",
    [
        "CREATE_VALIDATION_CYCLE",
        "MODIFY_REPORTS",
        "MODIFY_FINDINGS",
        "MODIFY_CREDITS",
        "MODIFY_BILLING",
        "MODIFY_MEMBERSHIP",
    ],
    ids=[
        "cannot-create-validation-cycle",
        "cannot-modify-reports",
        "cannot-modify-findings",
        "cannot-modify-credits",
        "cannot-modify-billing",
        "cannot-modify-membership",
    ],
)
def test_it_16_r1_s5_denies_every_reviewer_write(
    activity_name: str,
) -> None:
    """Deny every write capability named by the reviewer scenario."""

    authorize, activity, result = _reviewer_authorization_contract()
    assert hasattr(activity, activity_name), (
        f"IT-16R1S5 requires CustomerAccountActivity.{activity_name}."
    )

    decision = authorize(
        _active_reviewer(),
        "customer-account-1",
        getattr(activity, activity_name),
    )

    assert decision.result is result.DENIED
