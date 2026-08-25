"""Executable test for IT-16R1S4 validator report submission."""

from __future__ import annotations

from dataclasses import dataclass, field
from importlib import import_module
from typing import Any

import pytest

from app.services.customer_accounts import (
    CustomerAccountMembership,
    CustomerAccountRole,
)


ACCOUNT_VALIDATION_MODULE = "app.services.account_validation"


@dataclass(frozen=True)
class UadAppraisalReport:
    report_id: str


@dataclass(frozen=True)
class ValidationSubmission:
    validation_submission_id: str
    report_id: str
    customer_account_id: str
    actor_id: str


@dataclass(frozen=True)
class PendingValidationCycle:
    validation_cycle_id: str
    customer_account_id: str
    state: str


@dataclass(frozen=True)
class ValidationStartResult:
    submission: ValidationSubmission
    validation_cycle: PendingValidationCycle


@dataclass
class ValidationCycleGatewaySpy:
    calls: list[dict[str, str]] = field(default_factory=list)

    def start_new_report_validation(
        self,
        *,
        report_id: str,
        customer_account_id: str,
        actor_id: str,
    ) -> ValidationStartResult:
        self.calls.append(
            {
                "report_id": report_id,
                "customer_account_id": customer_account_id,
                "actor_id": actor_id,
            }
        )
        return ValidationStartResult(
            submission=ValidationSubmission(
                validation_submission_id="validation-submission-1",
                report_id=report_id,
                customer_account_id=customer_account_id,
                actor_id=actor_id,
            ),
            validation_cycle=PendingValidationCycle(
                validation_cycle_id="validation-cycle-1",
                customer_account_id=customer_account_id,
                state="pending",
            ),
        )


def _validator_submission_contract() -> Any:
    """Load the account-validation contract expected by IT-16R1S4."""

    try:
        module = import_module(ACCOUNT_VALIDATION_MODULE)
    except ModuleNotFoundError as error:
        if error.name != ACCOUNT_VALIDATION_MODULE:
            raise
        pytest.fail(
            "IT-16R1S4 requires app.services.account_validation before "
            "account-scoped validator submission can become green.",
            pytrace=False,
        )

    submit_report = getattr(
        module,
        "submit_report_for_customer_validation",
        None,
    )
    assert callable(submit_report), (
        "IT-16R1S4 requires submit_report_for_customer_validation("
        "membership, customer_account_id, report, validation_gateway)."
    )
    return submit_report


def test_it_16_r1_s4_scopes_validator_submission_and_cycle_to_account() -> None:
    """Scope the report, resulting cycle, and submitting actor together."""

    submit_report = _validator_submission_contract()
    customer_account_id = "customer-account-1"
    validator = CustomerAccountMembership(
        human_user_id="human-user-validator",
        customer_account_id=customer_account_id,
        role=CustomerAccountRole.VALIDATOR,
        active=True,
    )
    report = UadAppraisalReport(report_id="uad-report-1")
    validation_gateway = ValidationCycleGatewaySpy()

    result = submit_report(
        validator,
        customer_account_id,
        report,
        validation_gateway,
    )

    assert validation_gateway.calls == [
        {
            "report_id": report.report_id,
            "customer_account_id": customer_account_id,
            "actor_id": validator.human_user_id,
        }
    ]
    assert result.submission.report_id == report.report_id
    assert result.submission.customer_account_id == customer_account_id
    assert result.submission.actor_id == validator.human_user_id
    assert result.validation_cycle.customer_account_id == customer_account_id
    assert result.validation_cycle.state == "pending"
