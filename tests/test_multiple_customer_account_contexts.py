"""Executable test for IT-17R1S2 multiple account memberships."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from typing import Any

import pytest

from app.services.account_authorization import (
    AuthorizationResult,
    CustomerAccountActivity,
    authorize_customer_activity,
)
from app.services.customer_accounts import (
    CustomerAccountMembership,
    CustomerAccountRole,
)


ACCOUNT_CONTEXT_MODULE = "app.services.account_contexts"


@dataclass(frozen=True)
class AccountOwnedResource:
    resource_id: str
    customer_account_id: str


@dataclass(frozen=True)
class CustomerOwnedResources:
    reports: tuple[AccountOwnedResource, ...]
    validation_cycles: tuple[AccountOwnedResource, ...]
    credits: tuple[AccountOwnedResource, ...]
    billing_records: tuple[AccountOwnedResource, ...]


def _account_context_contract() -> Any:
    """Load the account-context contract expected by IT-17R1S2."""

    try:
        module = import_module(ACCOUNT_CONTEXT_MODULE)
    except ModuleNotFoundError as error:
        if error.name != ACCOUNT_CONTEXT_MODULE:
            raise
        pytest.fail(
            "IT-17R1S2 requires app.services.account_contexts before "
            "multiple-account context selection can become green.",
            pytrace=False,
        )

    select_context = getattr(
        module,
        "select_customer_account_context",
        None,
    )
    assert callable(select_context), (
        "IT-17R1S2 requires select_customer_account_context("
        "human_user_id, customer_account_id, memberships, resources)."
    )
    return select_context


def test_it_17_r1_s2_selects_one_of_a_persons_customer_accounts() -> None:
    """Scope permissions and resources without transferring ownership."""

    select_context = _account_context_contract()
    human_user_id = "human-user-1"
    account_1 = "customer-account-1"
    account_2 = "customer-account-2"
    memberships = (
        CustomerAccountMembership(
            human_user_id=human_user_id,
            customer_account_id=account_1,
            role=CustomerAccountRole.VALIDATOR,
            active=True,
        ),
        CustomerAccountMembership(
            human_user_id=human_user_id,
            customer_account_id=account_2,
            role=CustomerAccountRole.REVIEWER,
            active=True,
        ),
    )

    def resources_for(category: str) -> tuple[AccountOwnedResource, ...]:
        return (
            AccountOwnedResource(f"{category}-1", account_1),
            AccountOwnedResource(f"{category}-2", account_2),
        )

    resources = CustomerOwnedResources(
        reports=resources_for("report"),
        validation_cycles=resources_for("validation-cycle"),
        credits=resources_for("credit"),
        billing_records=resources_for("billing-record"),
    )
    original_resources = resources

    validator_context = select_context(
        human_user_id,
        account_1,
        memberships,
        resources,
    )
    reviewer_context = select_context(
        human_user_id,
        account_2,
        memberships,
        resources,
    )

    assert validator_context.customer_account_id == account_1
    assert validator_context.membership.role is CustomerAccountRole.VALIDATOR
    assert reviewer_context.customer_account_id == account_2
    assert reviewer_context.membership.role is CustomerAccountRole.REVIEWER

    validator_decision = authorize_customer_activity(
        validator_context.membership,
        validator_context.customer_account_id,
        CustomerAccountActivity.SUBMIT_REPORTS_AND_MANAGE_VALIDATION_CYCLES,
    )
    reviewer_decision = authorize_customer_activity(
        reviewer_context.membership,
        reviewer_context.customer_account_id,
        CustomerAccountActivity.SUBMIT_REPORTS_AND_MANAGE_VALIDATION_CYCLES,
    )
    assert validator_decision.result is AuthorizationResult.ALLOWED
    assert reviewer_decision.result is AuthorizationResult.DENIED

    for context in (validator_context, reviewer_context):
        visible_resources = (
            context.reports
            + context.validation_cycles
            + context.credits
            + context.billing_records
        )
        assert all(
            resource.customer_account_id == context.customer_account_id
            for resource in visible_resources
        )
        assert len(visible_resources) == 4

    assert resources == original_resources
    all_resources = (
        resources.reports
        + resources.validation_cycles
        + resources.credits
        + resources.billing_records
    )
    assert {resource.customer_account_id for resource in all_resources} == {
        account_1,
        account_2,
    }
