"""Lifecycle operations for account-scoped report-validation cycles."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.services.account_resource_access import (
    CustomerAccountResourceAccessDecision,
    ResourceAccessResult,
)


class UadAppraisalReport(Protocol):
    report_id: str


class ValidationCycleIdFactory(Protocol):
    def __call__(self) -> str: ...


class Clock(Protocol):
    def __call__(self) -> datetime: ...


class ValidationCycleRepository(Protocol):
    def save(self, validation_cycle: object) -> None: ...


class ValidationCycleAuthorization(Protocol):
    def authorize_new_cycle(
        self,
        customer_account_id: str,
        actor_id: str,
    ) -> None: ...


class ValidationCycleIdempotencyRepository(Protocol):
    def get(
        self,
        customer_account_id: str,
        idempotency_key: str,
    ) -> object | None: ...

    def save(
        self,
        customer_account_id: str,
        idempotency_key: str,
        validation_cycle: object,
    ) -> None: ...


class ValidationCycleAccessRepository(Protocol):
    def get_by_id(self, validation_cycle_id: str) -> object: ...


class ValidationCycleSecurityReviewHistory(Protocol):
    def record(self, **event: str) -> None: ...


class ReportRevision(Protocol):
    report_id: str


class ValidationCycleRevisionRepository(Protocol):
    def get_by_id(self, validation_cycle_id: str) -> object: ...

    def associate_report(
        self,
        validation_cycle_id: str,
        report: object,
    ) -> None: ...


@dataclass(frozen=True)
class PendingValidationCycle:
    """A newly accepted report awaiting its first validation outcome."""

    validation_cycle_id: str
    customer_account_id: str
    actor_id: str
    report_id: str
    state: str
    created_at: datetime


def create_pending_validation_cycle(
    customer_account_id: str,
    actor_id: str,
    report: UadAppraisalReport,
    cycle_id_factory: ValidationCycleIdFactory,
    clock: Clock,
    repository: ValidationCycleRepository,
) -> PendingValidationCycle:
    """Create, persist, and return one pending account-scoped cycle."""

    generated_cycle_id = cycle_id_factory()
    UUID(generated_cycle_id)
    validation_cycle = PendingValidationCycle(
        validation_cycle_id=generated_cycle_id,
        customer_account_id=customer_account_id,
        actor_id=actor_id,
        report_id=report.report_id,
        state="pending",
        created_at=clock(),
    )
    repository.save(validation_cycle)
    return validation_cycle


def create_pending_validation_cycle_idempotently(
    customer_account_id: str,
    actor_id: str,
    report: UadAppraisalReport,
    idempotency_key: str,
    authorization: ValidationCycleAuthorization,
    idempotency_repository: ValidationCycleIdempotencyRepository,
    cycle_id_factory: ValidationCycleIdFactory,
    clock: Clock,
    cycle_repository: ValidationCycleRepository,
) -> object:
    """Create a pending cycle once for an account-scoped request key."""

    existing_cycle = idempotency_repository.get(
        customer_account_id,
        idempotency_key,
    )
    if existing_cycle is not None:
        return existing_cycle

    authorization.authorize_new_cycle(customer_account_id, actor_id)
    validation_cycle = create_pending_validation_cycle(
        customer_account_id=customer_account_id,
        actor_id=actor_id,
        report=report,
        cycle_id_factory=cycle_id_factory,
        clock=clock,
        repository=cycle_repository,
    )
    idempotency_repository.save(
        customer_account_id,
        idempotency_key,
        validation_cycle,
    )
    return validation_cycle


def request_validation_cycle_access(
    customer_account_id: str,
    actor_id: str,
    validation_cycle_id: str,
    operation: str,
    repository: ValidationCycleAccessRepository,
    security_review_history: ValidationCycleSecurityReviewHistory,
) -> CustomerAccountResourceAccessDecision:
    """Disclose a cycle only within its owning customer-account boundary."""

    validation_cycle = repository.get_by_id(validation_cycle_id)
    if validation_cycle is None:
        raise LookupError(
            f"Validation cycle not found: {validation_cycle_id}"
        )

    protected_account_id = getattr(
        validation_cycle,
        "customer_account_id",
        None,
    )
    if protected_account_id == customer_account_id:
        return CustomerAccountResourceAccessDecision(
            result=ResourceAccessResult.ALLOWED,
            resource=validation_cycle,
        )

    security_review_history.record(
        event_type="cross_account_validation_cycle_access_denied",
        actor_customer_account_id=customer_account_id,
        protected_customer_account_id=protected_account_id or "",
        actor_id=actor_id,
        resource_type="validation cycle",
        resource_id=validation_cycle_id,
        operation=operation,
    )
    return CustomerAccountResourceAccessDecision(
        result=ResourceAccessResult.DENIED,
        resource=None,
    )


def associate_report_revision_with_cycle(
    validation_cycle_id: str,
    corrected_report: ReportRevision,
    repository: ValidationCycleRevisionRepository,
) -> object:
    """Associate a revision by explicit cycle ID without content matching."""

    validation_cycle = repository.get_by_id(validation_cycle_id)
    if validation_cycle is None:
        raise LookupError(
            f"Validation cycle not found: {validation_cycle_id}"
        )
    if getattr(validation_cycle, "validation_cycle_id", None) != (
        validation_cycle_id
    ):
        raise ValueError("The repository returned a different cycle.")
    if getattr(validation_cycle, "report_id", None) != (
        corrected_report.report_id
    ):
        raise ValueError(
            "A report revision must belong to the cycle's report."
        )

    repository.associate_report(
        validation_cycle_id,
        corrected_report,
    )
    return validation_cycle
