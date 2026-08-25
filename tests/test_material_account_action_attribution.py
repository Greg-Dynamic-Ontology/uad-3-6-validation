"""Executable test for IT-19R1S2 material-action attribution."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
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


ACCOUNT_AUDIT_MODULE = "app.services.account_audit"


@dataclass(frozen=True)
class EffectiveTimeClockStub:
    effective_time: datetime

    def now(self) -> datetime:
        return self.effective_time


@dataclass
class AccountAuditRepositorySpy:
    records: list[object] = field(default_factory=list)

    def add(self, record: object) -> None:
        self.records.append(record)


@dataclass
class MembershipRepositorySpy:
    saved_memberships: list[CustomerAccountMembership] = field(
        default_factory=list
    )

    def save(self, membership: CustomerAccountMembership) -> None:
        self.saved_memberships.append(membership)


@dataclass
class MembershipAuditHistorySpy:
    events: list[dict[str, object]] = field(default_factory=list)

    def record(self, **event: object) -> None:
        self.events.append(event)


def _material_action_audit_contract() -> tuple[Any, Any]:
    """Load the account-audit contract expected by IT-19R1S2."""

    try:
        module = import_module(ACCOUNT_AUDIT_MODULE)
    except ModuleNotFoundError as error:
        if error.name != ACCOUNT_AUDIT_MODULE:
            raise
        pytest.fail(
            "IT-19R1S2 requires app.services.account_audit before "
            "material-action attribution can become green.",
            pytrace=False,
        )

    record_action = getattr(
        module,
        "record_material_account_action",
        None,
    )
    action_outcome = getattr(module, "MaterialActionOutcome", None)
    assert callable(record_action), (
        "IT-19R1S2 requires record_material_account_action("
        "customer_account_id, actor_id, action, outcome, clock, "
        "audit_repository, affected_resource_id=None)."
    )
    assert action_outcome is not None, (
        "IT-19R1S2 requires MaterialActionOutcome."
    )
    assert hasattr(action_outcome, "ACCEPTED")
    assert hasattr(action_outcome, "DENIED")
    return record_action, action_outcome


def test_it_19_r1_s2_attributes_every_material_action_immutably() -> None:
    """Identify account, actor, action, time, outcome, and optional resource."""

    record_action, action_outcome = _material_action_audit_contract()
    customer_account_id = "customer-account-1"
    effective_time = datetime(2026, 8, 25, 14, 30, tzinfo=timezone.utc)
    clock = EffectiveTimeClockStub(effective_time)
    audit_repository = AccountAuditRepositorySpy()
    human_actor_id = "human-user-validator"
    software_actor_id = "software-client-1"

    accepted_record = record_action(
        customer_account_id,
        human_actor_id,
        "submit report for validation",
        action_outcome.ACCEPTED,
        clock,
        audit_repository,
        affected_resource_id="report-1",
    )
    denied_record = record_action(
        customer_account_id,
        software_actor_id,
        "access billing record",
        action_outcome.DENIED,
        clock,
        audit_repository,
    )

    assert audit_repository.records == [accepted_record, denied_record]
    assert accepted_record.customer_account_id == customer_account_id
    assert accepted_record.actor_id == human_actor_id
    assert accepted_record.action == "submit report for validation"
    assert accepted_record.outcome is action_outcome.ACCEPTED
    assert accepted_record.effective_time == effective_time
    assert accepted_record.affected_resource_id == "report-1"
    assert denied_record.customer_account_id == customer_account_id
    assert denied_record.actor_id == software_actor_id
    assert denied_record.action == "access billing record"
    assert denied_record.outcome is action_outcome.DENIED
    assert denied_record.effective_time == effective_time
    assert denied_record.affected_resource_id is None

    original_records = tuple(audit_repository.records)
    owner = CustomerAccountMembership(
        human_user_id="human-user-owner",
        customer_account_id=customer_account_id,
        role=CustomerAccountRole.OWNER,
        active=True,
    )
    human_membership = CustomerAccountMembership(
        human_user_id=human_actor_id,
        customer_account_id=customer_account_id,
        role=CustomerAccountRole.VALIDATOR,
        active=True,
    )
    remove_customer_account_membership(
        owner,
        human_membership,
        MembershipRepositorySpy(),
        MembershipAuditHistorySpy(),
    )

    assert tuple(audit_repository.records) == original_records
    assert accepted_record.actor_id == human_actor_id
