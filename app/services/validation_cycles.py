"""Lifecycle operations for account-scoped report-validation cycles."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum
from hashlib import sha256
from typing import Protocol
from uuid import UUID

from app.services.account_resource_access import (
    CustomerAccountResourceAccessDecision,
    ResourceAccessResult,
)


class MissingValidationCycleIdentifierError(ValueError):
    """Raised when a corrected submission does not identify its cycle."""


class ValidationAttemptAlreadyActiveError(RuntimeError):
    """Raised when a cycle already has a running validation attempt."""


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


class UadReportArtifact(Protocol):
    report_id: str
    content: bytes


class ValidationSubmissionIdFactory(Protocol):
    def __call__(self) -> str: ...


class ValidationAttemptIdFactory(Protocol):
    def __call__(self) -> str: ...


class ArtifactRetention(Protocol):
    def retain(
        self,
        artifact: object,
        integrity_digest: str,
    ) -> str: ...


class ValidationSubmissionRepository(Protocol):
    def save_submission(self, submission: object) -> None: ...


class CorrectedSubmissionRepository(ValidationSubmissionRepository, Protocol):
    def get_by_id(self, validation_cycle_id: str) -> object: ...


class ValidationAttemptRepository(Protocol):
    def get_active_for_cycle(
        self,
        validation_cycle_id: str,
    ) -> object | None: ...

    def save_attempt(self, validation_attempt: object) -> None: ...


class ValidationRunner(Protocol):
    def __call__(self, validation_attempt: object) -> object: ...


class CompletedValidatorResult(Protocol):
    ingestible: bool
    findings: tuple[object, ...]


class ValidationResultIdFactory(Protocol):
    def __call__(self) -> str: ...


class ValidationResultRepository(Protocol):
    def save_result(self, validation_result: object) -> None: ...


class FirstResultValidationCycleRepository(Protocol):
    def get_by_id(self, validation_cycle_id: str) -> object: ...

    def submission_belongs_to_cycle(
        self,
        validation_cycle_id: str,
        validation_submission_id: str,
    ) -> bool: ...

    def save(self, validation_cycle: object) -> None: ...


class CreditLifecycleEventPublisher(Protocol):
    def publish(self, lifecycle_event: object) -> None: ...


class CancellationValidationCycleRepository(Protocol):
    def get_by_id(self, validation_cycle_id: str) -> object: ...

    def save(self, validation_cycle: object) -> None: ...

    def append_history_event(
        self,
        validation_cycle_id: str,
        lifecycle_event: object,
    ) -> None: ...


class ServiceFailureValidationCycleRepository(
    CancellationValidationCycleRepository,
    Protocol,
):
    def submission_belongs_to_cycle(
        self,
        validation_cycle_id: str,
        validation_submission_id: str,
    ) -> bool: ...


class CorrectedResultValidationCycleRepository(Protocol):
    def get_by_id(self, validation_cycle_id: str) -> object: ...

    def submission_belongs_to_cycle(
        self,
        validation_cycle_id: str,
        validation_submission_id: str,
    ) -> bool: ...

    def save(self, validation_cycle: object) -> None: ...

    def append_result_history(
        self,
        validation_cycle_id: str,
        validation_result_id: str,
    ) -> None: ...


class CustomerValidationNotifier(Protocol):
    def notify_validation_passed(
        self,
        validation_cycle_id: str,
        validation_result_id: str,
        message: str,
    ) -> None: ...


class ValidationCompletionEvent(Protocol):
    completion_event_id: str
    validation_cycle_id: str
    validation_attempt_id: str
    validation_submission_id: str
    validation_result_id: str


class ValidationCompletionRepository(Protocol):
    def has_applied_completion_event(
        self,
        completion_event_id: str,
    ) -> bool: ...

    def get_by_id(self, validation_cycle_id: str) -> object: ...

    def append_result_history(
        self,
        validation_cycle_id: str,
        validation_result_id: str,
    ) -> None: ...

    def mark_completion_event_applied(
        self,
        completion_event_id: str,
    ) -> None: ...


class CompletionEventAudit(Protocol):
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
    current_validation_result_id: str | None = None
    billable_validation_service_delivered: bool | None = None


@dataclass(frozen=True)
class AcceptedValidationSubmission:
    """An immutable record of one accepted report artifact."""

    validation_submission_id: str
    validation_cycle_id: str
    report_id: str
    accepted_at: datetime
    integrity_digest: str
    artifact_reference: str


@dataclass(frozen=True)
class RunningValidationAttempt:
    """One validation attempt currently executing for a cycle."""

    validation_attempt_id: str
    validation_cycle_id: str
    validation_submission_id: str
    state: str
    started_at: datetime


@dataclass(frozen=True)
class ActionableValidationResult:
    """A completed result that a customer can act upon."""

    validation_result_id: str
    validation_submission_id: str
    actionable: bool
    passed: bool
    findings: tuple[object, ...]
    completed_at: datetime


@dataclass(frozen=True)
class ValidationCycleBillableServiceEvent:
    """A lifecycle transition made available to credit management."""

    event_type: str
    validation_cycle_id: str
    validation_result_id: str
    previous_state: str
    current_state: str
    billable_validation_service_delivered: bool
    occurred_at: datetime


@dataclass(frozen=True)
class ValidationCycleCancellationEvent:
    """A non-billable cancellation retained in cycle history."""

    event_type: str
    validation_cycle_id: str
    previous_state: str
    current_state: str
    billable_validation_service_delivered: bool
    failure_category: str
    failure_reason: str
    occurred_at: datetime


class ValidationCompletionEventDisposition(StrEnum):
    """Outcomes from receiving a validation-completion event."""

    APPLIED = "applied"
    DUPLICATE_IGNORED = "duplicate-ignored"


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


def accept_report_submission(
    validation_cycle_id: str,
    report_artifact: UadReportArtifact,
    submission_id_factory: ValidationSubmissionIdFactory,
    clock: Clock,
    artifact_retention: ArtifactRetention,
    repository: ValidationSubmissionRepository,
) -> AcceptedValidationSubmission:
    """Assign identity and traceability to one accepted report artifact."""

    validation_submission_id = submission_id_factory()
    UUID(validation_submission_id)
    integrity_digest = sha256(report_artifact.content).hexdigest()
    artifact_reference = artifact_retention.retain(
        report_artifact,
        integrity_digest,
    )
    submission = AcceptedValidationSubmission(
        validation_submission_id=validation_submission_id,
        validation_cycle_id=validation_cycle_id,
        report_id=report_artifact.report_id,
        accepted_at=clock(),
        integrity_digest=integrity_digest,
        artifact_reference=artifact_reference,
    )
    repository.save_submission(submission)
    return submission


def accept_corrected_report_submission(
    validation_cycle_id: str | None,
    corrected_report_artifact: UadReportArtifact,
    submission_id_factory: ValidationSubmissionIdFactory,
    clock: Clock,
    artifact_retention: ArtifactRetention,
    repository: CorrectedSubmissionRepository,
) -> AcceptedValidationSubmission:
    """Accept a correction only into its explicitly identified open cycle."""

    if not validation_cycle_id:
        raise MissingValidationCycleIdentifierError(
            "A validation cycle identifier is required for a corrected "
            "submission."
        )

    validation_cycle = repository.get_by_id(validation_cycle_id)
    if validation_cycle is None:
        raise LookupError(
            f"Validation cycle not found: {validation_cycle_id}"
        )
    if getattr(validation_cycle, "validation_cycle_id", None) != (
        validation_cycle_id
    ):
        raise ValueError("The repository returned a different cycle.")
    if getattr(validation_cycle, "state", None) != "open":
        raise ValueError("Corrected reports require an open validation cycle.")
    if getattr(validation_cycle, "report_id", None) != (
        corrected_report_artifact.report_id
    ):
        raise ValueError(
            "A corrected report must belong to the cycle's report."
        )

    return accept_report_submission(
        validation_cycle_id=validation_cycle_id,
        report_artifact=corrected_report_artifact,
        submission_id_factory=submission_id_factory,
        clock=clock,
        artifact_retention=artifact_retention,
        repository=repository,
    )


def start_validation_attempt(
    validation_cycle_id: str,
    validation_submission_id: str,
    attempt_id_factory: ValidationAttemptIdFactory,
    clock: Clock,
    validation_runner: ValidationRunner,
    repository: ValidationAttemptRepository,
) -> RunningValidationAttempt:
    """Start validation only when the cycle has no active attempt."""

    active_attempt = repository.get_active_for_cycle(validation_cycle_id)
    if active_attempt is not None:
        raise ValidationAttemptAlreadyActiveError(
            f"Validation cycle {validation_cycle_id} already has an "
            "active validation attempt."
        )

    validation_attempt_id = attempt_id_factory()
    UUID(validation_attempt_id)
    validation_attempt = RunningValidationAttempt(
        validation_attempt_id=validation_attempt_id,
        validation_cycle_id=validation_cycle_id,
        validation_submission_id=validation_submission_id,
        state="running",
        started_at=clock(),
    )
    repository.save_attempt(validation_attempt)
    validation_runner(validation_attempt)
    return validation_attempt


def produce_actionable_validation_result(
    validation_submission_id: str,
    validator_result: CompletedValidatorResult,
    result_id_factory: ValidationResultIdFactory,
    clock: Clock,
    repository: ValidationResultRepository,
) -> ActionableValidationResult:
    """Record findings or a pass for one ingestible report submission."""

    if not validator_result.ingestible:
        raise ValueError(
            "A non-ingestible artifact cannot produce an actionable "
            "validation result."
        )

    validation_result_id = result_id_factory()
    UUID(validation_result_id)
    findings = tuple(validator_result.findings)
    result = ActionableValidationResult(
        validation_result_id=validation_result_id,
        validation_submission_id=validation_submission_id,
        actionable=True,
        passed=not findings,
        findings=findings,
        completed_at=clock(),
    )
    repository.save_result(result)
    return result


def apply_first_actionable_validation_result(
    validation_cycle_id: str,
    validation_result: ActionableValidationResult,
    clock: Clock,
    repository: FirstResultValidationCycleRepository,
    credit_event_publisher: CreditLifecycleEventPublisher,
) -> object:
    """Determine a pending cycle's state from its first actionable result."""

    validation_cycle = repository.get_by_id(validation_cycle_id)
    if validation_cycle is None:
        raise LookupError(
            f"Validation cycle not found: {validation_cycle_id}"
        )
    if getattr(validation_cycle, "validation_cycle_id", None) != (
        validation_cycle_id
    ):
        raise ValueError("The repository returned a different cycle.")
    if getattr(validation_cycle, "state", None) != "pending":
        raise ValueError("The first result requires a pending cycle.")
    if getattr(validation_cycle, "current_validation_result_id", None):
        raise ValueError("The validation cycle already has a current result.")
    if not validation_result.actionable:
        raise ValueError(
            "A pending cycle outcome requires an actionable result."
        )
    if validation_result.passed and validation_result.findings:
        raise ValueError("A result with findings cannot be passing.")
    if not validation_result.passed and not validation_result.findings:
        raise ValueError("A failing result must contain findings.")
    if not repository.submission_belongs_to_cycle(
        validation_cycle_id,
        validation_result.validation_submission_id,
    ):
        raise ValueError(
            "The validation result belongs to another submission or cycle."
        )

    next_state = (
        "passed-and-closed" if validation_result.passed else "open"
    )
    updated_cycle = replace(
        validation_cycle,
        state=next_state,
        current_validation_result_id=validation_result.validation_result_id,
        billable_validation_service_delivered=True,
    )
    repository.save(updated_cycle)
    credit_event_publisher.publish(
        ValidationCycleBillableServiceEvent(
            event_type="billable_validation_service_delivered",
            validation_cycle_id=validation_cycle_id,
            validation_result_id=validation_result.validation_result_id,
            previous_state="pending",
            current_state=next_state,
            billable_validation_service_delivered=True,
            occurred_at=clock(),
        )
    )
    return updated_cycle


def apply_corrected_actionable_validation_result(
    validation_cycle_id: str,
    validation_result: ActionableValidationResult,
    repository: CorrectedResultValidationCycleRepository,
    customer_notifier: CustomerValidationNotifier | None = None,
) -> object:
    """Apply a corrected result without overwriting prior result history."""

    validation_cycle = repository.get_by_id(validation_cycle_id)
    if validation_cycle is None:
        raise LookupError(
            f"Validation cycle not found: {validation_cycle_id}"
        )
    if getattr(validation_cycle, "validation_cycle_id", None) != (
        validation_cycle_id
    ):
        raise ValueError("The repository returned a different cycle.")
    if getattr(validation_cycle, "state", None) != "open":
        raise ValueError("A corrected result requires an open cycle.")
    if not validation_result.actionable:
        raise ValueError("A correction requires an actionable result.")
    if validation_result.passed and validation_result.findings:
        raise ValueError("A passing correction cannot contain findings.")
    if not validation_result.passed and not validation_result.findings:
        raise ValueError("A failing correction must contain findings.")
    if validation_result.passed and customer_notifier is None:
        raise ValueError("A passing correction requires customer notification.")
    if not repository.submission_belongs_to_cycle(
        validation_cycle_id,
        validation_result.validation_submission_id,
    ):
        raise ValueError(
            "The corrected result belongs to another submission or cycle."
        )

    next_state = (
        "passed-and-closed" if validation_result.passed else "open"
    )
    updated_cycle = replace(
        validation_cycle,
        state=next_state,
        current_validation_result_id=validation_result.validation_result_id,
    )
    repository.save(updated_cycle)
    repository.append_result_history(
        validation_cycle_id,
        validation_result.validation_result_id,
    )
    if validation_result.passed:
        assert customer_notifier is not None
        customer_notifier.notify_validation_passed(
            validation_cycle_id,
            validation_result.validation_result_id,
            "The report passed this validation service.",
        )
    return updated_cycle


def cancel_pending_cycle_for_ingestion_failure(
    validation_cycle_id: str,
    failure_reason: str,
    clock: Clock,
    repository: CancellationValidationCycleRepository,
    credit_event_publisher: CreditLifecycleEventPublisher,
) -> object:
    """Cancel a pending cycle when its artifact cannot be ingested."""

    validation_cycle = repository.get_by_id(validation_cycle_id)
    if validation_cycle is None:
        raise LookupError(
            f"Validation cycle not found: {validation_cycle_id}"
        )
    if getattr(validation_cycle, "validation_cycle_id", None) != (
        validation_cycle_id
    ):
        raise ValueError("The repository returned a different cycle.")
    if getattr(validation_cycle, "state", None) != "pending":
        raise ValueError("Only a pending cycle can be cancelled this way.")
    if not failure_reason.strip():
        raise ValueError("An ingestion failure reason is required.")

    cancelled_cycle = replace(
        validation_cycle,
        state="cancelled",
        current_validation_result_id=None,
        billable_validation_service_delivered=False,
    )
    cancellation_event = ValidationCycleCancellationEvent(
        event_type="validation_cycle_cancelled",
        validation_cycle_id=validation_cycle_id,
        previous_state="pending",
        current_state="cancelled",
        billable_validation_service_delivered=False,
        failure_category="artifact-ingestion-failure",
        failure_reason=failure_reason,
        occurred_at=clock(),
    )
    repository.save(cancelled_cycle)
    repository.append_history_event(
        validation_cycle_id,
        cancellation_event,
    )
    credit_event_publisher.publish(cancellation_event)
    return cancelled_cycle


def cancel_pending_cycle_for_validation_service_failure(
    validation_cycle_id: str,
    validation_submission_id: str,
    failure_reason: str,
    clock: Clock,
    repository: ServiceFailureValidationCycleRepository,
    credit_event_publisher: CreditLifecycleEventPublisher,
) -> object:
    """Cancel a pending cycle when validation cannot produce a result."""

    validation_cycle = repository.get_by_id(validation_cycle_id)
    if validation_cycle is None:
        raise LookupError(
            f"Validation cycle not found: {validation_cycle_id}"
        )
    if getattr(validation_cycle, "validation_cycle_id", None) != (
        validation_cycle_id
    ):
        raise ValueError("The repository returned a different cycle.")
    if getattr(validation_cycle, "state", None) != "pending":
        raise ValueError("Only a pending cycle can be cancelled this way.")
    if not repository.submission_belongs_to_cycle(
        validation_cycle_id,
        validation_submission_id,
    ):
        raise ValueError(
            "The failed submission belongs to another validation cycle."
        )
    if not failure_reason.strip():
        raise ValueError("A validation-service failure reason is required.")

    cancelled_cycle = replace(
        validation_cycle,
        state="cancelled",
        current_validation_result_id=None,
        billable_validation_service_delivered=False,
    )
    cancellation_event = ValidationCycleCancellationEvent(
        event_type="validation_cycle_cancelled",
        validation_cycle_id=validation_cycle_id,
        previous_state="pending",
        current_state="cancelled",
        billable_validation_service_delivered=False,
        failure_category="validation-service-failure",
        failure_reason=failure_reason,
        occurred_at=clock(),
    )
    repository.save(cancelled_cycle)
    repository.append_history_event(
        validation_cycle_id,
        cancellation_event,
    )
    credit_event_publisher.publish(cancellation_event)
    return cancelled_cycle


def apply_validation_completion_event(
    completion_event: ValidationCompletionEvent,
    repository: ValidationCompletionRepository,
    credit_event_publisher: CreditLifecycleEventPublisher,
    audit: CompletionEventAudit,
) -> ValidationCompletionEventDisposition:
    """Apply a completion event no more than once by stable event identity."""

    if repository.has_applied_completion_event(
        completion_event.completion_event_id
    ):
        audit.record(
            event_type="duplicate_validation_completion_event_ignored",
            completion_event_id=completion_event.completion_event_id,
            validation_cycle_id=completion_event.validation_cycle_id,
            validation_attempt_id=completion_event.validation_attempt_id,
            validation_submission_id=(
                completion_event.validation_submission_id
            ),
            validation_result_id=completion_event.validation_result_id,
        )
        return ValidationCompletionEventDisposition.DUPLICATE_IGNORED

    repository.get_by_id(completion_event.validation_cycle_id)
    repository.append_result_history(
        completion_event.validation_cycle_id,
        completion_event.validation_result_id,
    )
    repository.mark_completion_event_applied(
        completion_event.completion_event_id
    )
    credit_event_publisher.publish(completion_event)
    return ValidationCompletionEventDisposition.APPLIED


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
