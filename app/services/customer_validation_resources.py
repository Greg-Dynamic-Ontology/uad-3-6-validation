"""Customer ownership and access for reports and validation cycles."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.services.customer_accounts import CustomerAccountMembership


class ReportArtifact(Protocol):
    report_artifact_id: str


class ValidationCycle(Protocol):
    validation_cycle_id: str


@dataclass(frozen=True)
class CustomerOwnedReportArtifact:
    """A report artifact durably owned by one customer account."""

    report_artifact_id: str
    customer_account_id: str
    actor_id: str


@dataclass(frozen=True)
class CustomerOwnedValidationCycle:
    """A validation cycle durably owned by one customer account."""

    validation_cycle_id: str
    customer_account_id: str
    actor_id: str


@dataclass(frozen=True)
class CustomerValidationResources:
    """A report artifact and cycle created in the same account scope."""

    report_artifact: CustomerOwnedReportArtifact
    validation_cycle: CustomerOwnedValidationCycle


@dataclass(frozen=True)
class CustomerValidationResourceView:
    """Retained validation resources visible in an account context."""

    report_artifacts: tuple[CustomerOwnedReportArtifact, ...]
    validation_cycles: tuple[CustomerOwnedValidationCycle, ...]


class CustomerValidationResourceRepository(Protocol):
    def add_report_artifact(
        self,
        report_artifact: CustomerOwnedReportArtifact,
    ) -> None: ...

    def add_validation_cycle(
        self,
        validation_cycle: CustomerOwnedValidationCycle,
    ) -> None: ...

    def list_report_artifacts(
        self,
    ) -> tuple[CustomerOwnedReportArtifact, ...]: ...

    def list_validation_cycles(
        self,
    ) -> tuple[CustomerOwnedValidationCycle, ...]: ...


class RetentionPolicy(Protocol):
    def retains(
        self,
        resource: CustomerOwnedReportArtifact | CustomerOwnedValidationCycle,
    ) -> bool: ...


def assign_customer_validation_resource_ownership(
    actor_id: str,
    customer_account_id: str,
    report_artifact: ReportArtifact,
    validation_cycle: ValidationCycle,
    repository: CustomerValidationResourceRepository,
) -> CustomerValidationResources:
    """Persist report and cycle ownership at the customer-account boundary."""

    owned_report_artifact = CustomerOwnedReportArtifact(
        report_artifact_id=report_artifact.report_artifact_id,
        customer_account_id=customer_account_id,
        actor_id=actor_id,
    )
    owned_validation_cycle = CustomerOwnedValidationCycle(
        validation_cycle_id=validation_cycle.validation_cycle_id,
        customer_account_id=customer_account_id,
        actor_id=actor_id,
    )
    repository.add_report_artifact(owned_report_artifact)
    repository.add_validation_cycle(owned_validation_cycle)
    return CustomerValidationResources(
        report_artifact=owned_report_artifact,
        validation_cycle=owned_validation_cycle,
    )


def access_customer_validation_resources(
    membership: CustomerAccountMembership,
    customer_account_id: str,
    repository: CustomerValidationResourceRepository,
    retention_policy: RetentionPolicy,
) -> CustomerValidationResourceView:
    """Expose only retained resources through an active account membership."""

    if (
        not membership.active
        or membership.customer_account_id != customer_account_id
    ):
        raise PermissionError(
            "An active membership in this customer account is required."
        )

    report_artifacts = tuple(
        resource
        for resource in repository.list_report_artifacts()
        if resource.customer_account_id == customer_account_id
        and retention_policy.retains(resource)
    )
    validation_cycles = tuple(
        resource
        for resource in repository.list_validation_cycles()
        if resource.customer_account_id == customer_account_id
        and retention_policy.retains(resource)
    )
    return CustomerValidationResourceView(
        report_artifacts=report_artifacts,
        validation_cycles=validation_cycles,
    )
