"""Acceptance tests for IT-25R2S4 validation-cycle account isolation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from importlib import import_module
from typing import Any

import pytest


VALIDATION_CYCLES_MODULE = "app.services.validation_cycles"


@dataclass
class ValidationCycleRepositorySpy:
    validation_cycle: object
    lookups: list[str] = field(default_factory=list)
    saved_cycles: list[object] = field(default_factory=list)
    report_associations: list[tuple[str, object]] = field(
        default_factory=list
    )

    def get_by_id(self, validation_cycle_id: str) -> object:
        self.lookups.append(validation_cycle_id)
        return self.validation_cycle

    def save(self, validation_cycle: object) -> None:
        self.saved_cycles.append(validation_cycle)

    def associate_report(
        self,
        validation_cycle_id: str,
        report: object,
    ) -> None:
        self.report_associations.append((validation_cycle_id, report))


@dataclass
class SecurityReviewHistorySpy:
    events: list[dict[str, str]] = field(default_factory=list)

    def record(self, **event: str) -> None:
        self.events.append(event)


def _cycle_access_contract() -> tuple[Any, type[Any], Any]:
    """Load the account-scoped cycle-access contract for IT-25R2S4."""

    module = import_module(VALIDATION_CYCLES_MODULE)
    request_access = getattr(
        module,
        "request_validation_cycle_access",
        None,
    )
    pending_cycle = getattr(module, "PendingValidationCycle", None)

    resource_access = import_module("app.services.account_resource_access")
    access_result = getattr(resource_access, "ResourceAccessResult", None)

    assert callable(request_access), (
        "IT-25R2S4 requires request_validation_cycle_access("
        "customer_account_id, actor_id, validation_cycle_id, operation, "
        "repository, security_review_history)."
    )
    assert isinstance(pending_cycle, type)
    assert access_result is not None and hasattr(access_result, "DENIED")
    return request_access, pending_cycle, access_result


@pytest.mark.parametrize(
    "operation",
    ["request-cycle", "submit-report"],
    ids=["request-cycle", "submit-report"],
)
def test_it_25_r2_s4_denies_cross_account_cycle_access(
    operation: str,
) -> None:
    """Deny disclosure and mutation, then record the denied request."""

    request_access, pending_cycle, access_result = _cycle_access_contract()
    owner_account_id = "customer-account-owner"
    requesting_account_id = "customer-account-other"
    validation_cycle_id = "6ad8df4d-df4a-4a2f-925e-2f57df436c92"
    cycle = pending_cycle(
        validation_cycle_id=validation_cycle_id,
        customer_account_id=owner_account_id,
        actor_id="human-user-owner",
        report_id="protected-report-1",
        state="pending",
        created_at=datetime(2026, 8, 27, 15, 30, tzinfo=timezone.utc),
    )
    original_cycle = cycle
    repository = ValidationCycleRepositorySpy(cycle)
    security_review_history = SecurityReviewHistorySpy()

    decision = request_access(
        customer_account_id=requesting_account_id,
        actor_id="human-user-other",
        validation_cycle_id=validation_cycle_id,
        operation=operation,
        repository=repository,
        security_review_history=security_review_history,
    )

    assert decision.result is access_result.DENIED
    assert decision.resource is None
    assert repository.validation_cycle == original_cycle
    assert repository.saved_cycles == []
    assert repository.report_associations == []
    assert security_review_history.events == [
        {
            "event_type": "cross_account_validation_cycle_access_denied",
            "actor_customer_account_id": requesting_account_id,
            "protected_customer_account_id": owner_account_id,
            "actor_id": "human-user-other",
            "resource_type": "validation cycle",
            "resource_id": validation_cycle_id,
            "operation": operation,
        }
    ]
