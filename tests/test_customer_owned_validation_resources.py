"""Executable test for IT-18R1S2 customer-owned validation resources."""

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


VALIDATION_RESOURCES_MODULE = "app.services.customer_validation_resources"


@dataclass(frozen=True)
class ReportArtifact:
    report_artifact_id: str


@dataclass(frozen=True)
class ValidationCycle:
    validation_cycle_id: str


@dataclass
class CustomerValidationResourceRepositorySpy:
    report_artifacts: list[object] = field(default_factory=list)
    validation_cycles: list[object] = field(default_factory=list)

    def add_report_artifact(self, report_artifact: object) -> None:
        self.report_artifacts.append(report_artifact)

    def add_validation_cycle(self, validation_cycle: object) -> None:
        self.validation_cycles.append(validation_cycle)

    def list_report_artifacts(self) -> tuple[object, ...]:
        return tuple(self.report_artifacts)

    def list_validation_cycles(self) -> tuple[object, ...]:
        return tuple(self.validation_cycles)


@dataclass
class RetentionPolicySpy:
    evaluated_resource_ids: list[str] = field(default_factory=list)

    def retains(self, resource: object) -> bool:
        resource_id = getattr(
            resource,
            "report_artifact_id",
            getattr(resource, "validation_cycle_id", ""),
        )
        self.evaluated_resource_ids.append(resource_id)
        return True


@dataclass
class MembershipRepositorySpy:
    saved_memberships: list[CustomerAccountMembership] = field(
        default_factory=list
    )

    def save(self, membership: CustomerAccountMembership) -> None:
        self.saved_memberships.append(membership)


@dataclass
class AuditHistorySpy:
    events: list[dict[str, object]] = field(default_factory=list)

    def record(self, **event: object) -> None:
        self.events.append(event)


def _validation_resource_contract() -> tuple[Any, Any]:
    """Load the resource-ownership contract expected by IT-18R1S2."""

    try:
        module = import_module(VALIDATION_RESOURCES_MODULE)
    except ModuleNotFoundError as error:
        if error.name != VALIDATION_RESOURCES_MODULE:
            raise
        pytest.fail(
            "IT-18R1S2 requires app.services.customer_validation_resources "
            "before report and cycle ownership can become green.",
            pytrace=False,
        )

    assign_ownership = getattr(
        module,
        "assign_customer_validation_resource_ownership",
        None,
    )
    access_resources = getattr(
        module,
        "access_customer_validation_resources",
        None,
    )
    assert callable(assign_ownership), (
        "IT-18R1S2 requires "
        "assign_customer_validation_resource_ownership(actor_id, "
        "customer_account_id, report_artifact, validation_cycle, repository)."
    )
    assert callable(access_resources), (
        "IT-18R1S2 requires access_customer_validation_resources("
        "membership, customer_account_id, repository, retention_policy)."
    )
    return assign_ownership, access_resources


def test_it_18_r1_s2_makes_reports_and_cycles_customer_owned() -> None:
    """Preserve account ownership and enforce membership plus retention."""

    assign_ownership, access_resources = _validation_resource_contract()
    customer_account_id = "customer-account-1"
    owner = CustomerAccountMembership(
        human_user_id="human-user-owner",
        customer_account_id=customer_account_id,
        role=CustomerAccountRole.OWNER,
        active=True,
    )
    acting_member = CustomerAccountMembership(
        human_user_id="human-user-validator",
        customer_account_id=customer_account_id,
        role=CustomerAccountRole.VALIDATOR,
        active=True,
    )
    report_artifact = ReportArtifact("report-artifact-1")
    validation_cycle = ValidationCycle("validation-cycle-1")
    resources = CustomerValidationResourceRepositorySpy()

    owned = assign_ownership(
        acting_member.human_user_id,
        customer_account_id,
        report_artifact,
        validation_cycle,
        resources,
    )

    assert owned.report_artifact.customer_account_id == customer_account_id
    assert owned.validation_cycle.customer_account_id == customer_account_id
    assert resources.report_artifacts == [owned.report_artifact]
    assert resources.validation_cycles == [owned.validation_cycle]

    removed_member = remove_customer_account_membership(
        owner,
        acting_member,
        MembershipRepositorySpy(),
        AuditHistorySpy(),
    )
    assert resources.report_artifacts == [owned.report_artifact]
    assert resources.validation_cycles == [owned.validation_cycle]
    assert owned.report_artifact.customer_account_id == customer_account_id
    assert owned.validation_cycle.customer_account_id == customer_account_id

    retention_policy = RetentionPolicySpy()
    with pytest.raises(PermissionError):
        access_resources(
            removed_member,
            customer_account_id,
            resources,
            retention_policy,
        )

    active_reviewer = CustomerAccountMembership(
        human_user_id="human-user-reviewer",
        customer_account_id=customer_account_id,
        role=CustomerAccountRole.REVIEWER,
        active=True,
    )
    visible = access_resources(
        active_reviewer,
        customer_account_id,
        resources,
        retention_policy,
    )

    assert visible.report_artifacts == (owned.report_artifact,)
    assert visible.validation_cycles == (owned.validation_cycle,)
    assert retention_policy.evaluated_resource_ids == [
        report_artifact.report_artifact_id,
        validation_cycle.validation_cycle_id,
    ]
