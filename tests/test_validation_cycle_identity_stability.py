"""Acceptance test for IT-25R2S2 stable validation-cycle identity."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from importlib import import_module
from typing import Any

import pytest


VALIDATION_CYCLES_MODULE = "app.services.validation_cycles"


@dataclass(frozen=True)
class CorrectedUadAppraisalReport:
    report_id: str
    serialized_content: bytes
    gse_submission_id: str


@dataclass
class ValidationCycleRepositorySpy:
    validation_cycle: object
    cycle_id_lookups: list[str] = field(default_factory=list)
    content_comparisons: list[bytes] = field(default_factory=list)
    report_associations: list[tuple[str, object]] = field(
        default_factory=list
    )

    def get_by_id(self, validation_cycle_id: str) -> object:
        self.cycle_id_lookups.append(validation_cycle_id)
        return self.validation_cycle

    def find_by_report_content(self, serialized_content: bytes) -> object:
        self.content_comparisons.append(serialized_content)
        raise AssertionError(
            "IT-25R2S2 forbids inferring cycle identity from report files."
        )

    def associate_report(
        self,
        validation_cycle_id: str,
        report: object,
    ) -> None:
        self.report_associations.append((validation_cycle_id, report))


def _identity_contract() -> tuple[Any, type[Any]]:
    """Load the stable-cycle identity contract required by IT-25R2S2."""

    try:
        module = import_module(VALIDATION_CYCLES_MODULE)
    except ModuleNotFoundError as error:
        if error.name != VALIDATION_CYCLES_MODULE:
            raise
        pytest.fail(
            "IT-25R2S2 requires app.services.validation_cycles before "
            "cycle identity stability can become green.",
            pytrace=False,
        )

    associate_revision = getattr(
        module,
        "associate_report_revision_with_cycle",
        None,
    )
    pending_cycle = getattr(module, "PendingValidationCycle", None)
    assert callable(associate_revision), (
        "IT-25R2S2 requires associate_report_revision_with_cycle("
        "validation_cycle_id, corrected_report, repository)."
    )
    assert isinstance(pending_cycle, type)
    return associate_revision, pending_cycle


def test_it_25_r2_s2_keeps_identity_independent_of_report_content() -> None:
    """Use the supplied cycle ID rather than report or GSE identities."""

    associate_revision, pending_cycle = _identity_contract()
    validation_cycle_id = "6ad8df4d-df4a-4a2f-925e-2f57df436c92"
    cycle = pending_cycle(
        validation_cycle_id=validation_cycle_id,
        customer_account_id="customer-account-1",
        actor_id="human-user-validator",
        report_id="uad-report-1",
        state="pending",
        created_at=datetime(
            2026,
            8,
            27,
            15,
            30,
            tzinfo=timezone.utc,
        ),
    )
    corrected_report = CorrectedUadAppraisalReport(
        report_id=cycle.report_id,
        serialized_content=b"corrected serialized UAD report",
        gse_submission_id="FNM-SUBMISSION-92851",
    )
    repository = ValidationCycleRepositorySpy(cycle)

    resulting_cycle = associate_revision(
        validation_cycle_id,
        corrected_report,
        repository,
    )

    assert resulting_cycle.validation_cycle_id == validation_cycle_id
    assert resulting_cycle.validation_cycle_id != (
        corrected_report.gse_submission_id
    )
    assert repository.cycle_id_lookups == [validation_cycle_id]
    assert repository.content_comparisons == []
    assert repository.report_associations == [
        (validation_cycle_id, corrected_report)
    ]
