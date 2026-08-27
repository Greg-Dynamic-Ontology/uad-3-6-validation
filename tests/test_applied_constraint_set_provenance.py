"""Acceptance test for IT-24R1S7 applied-set provenance."""

from __future__ import annotations

from dataclasses import dataclass, field
from importlib import import_module
from typing import Any

import pytest


CONSTRAINT_COMPOSITION_MODULE = (
    "app.services.constraint_set_composition"
)


@dataclass(frozen=True)
class GovernedConstraintSet:
    constraint_set_id: str
    authority: str
    version: str


@dataclass
class ConstraintSetProvenanceRepositorySpy:
    saved_records: list[object] = field(default_factory=list)

    def save(self, provenance_record: object) -> None:
        self.saved_records.append(provenance_record)


def _provenance_contract() -> Any:
    """Load the provenance operation required by IT-24R1S7."""

    try:
        module = import_module(CONSTRAINT_COMPOSITION_MODULE)
    except ModuleNotFoundError as error:
        if error.name != CONSTRAINT_COMPOSITION_MODULE:
            raise
        pytest.fail(
            "IT-24R1S7 requires app.services.constraint_set_composition "
            "before applied-set provenance can become green.",
            pytrace=False,
        )

    record_provenance = getattr(
        module,
        "record_applied_constraint_set_provenance",
        None,
    )
    assert callable(record_provenance), (
        "IT-24R1S7 requires "
        "record_applied_constraint_set_provenance("
        "validation_cycle_id, effective_constraint_sets, repository)."
    )
    return record_provenance


def test_it_24_r1_s7_records_provenance_of_every_applied_constraint_set(
) -> None:
    """Record authority, set identity, and version for every applied set."""

    record_provenance = _provenance_contract()
    validation_cycle_id = "validation-cycle-1"
    effective_constraint_sets = (
        GovernedConstraintSet(
            constraint_set_id="shared-uad36",
            authority="gse",
            version="2026.1",
        ),
        GovernedConstraintSet(
            constraint_set_id="lender-1-overlay",
            authority="lender-1",
            version="2026.08",
        ),
        GovernedConstraintSet(
            constraint_set_id="amc-1-overlay",
            authority="amc-1",
            version="4.2",
        ),
    )
    repository = ConstraintSetProvenanceRepositorySpy()

    recorded_provenance = record_provenance(
        validation_cycle_id,
        effective_constraint_sets,
        repository,
    )

    assert tuple(
        (
            record.validation_cycle_id,
            record.authority,
            record.constraint_set_id,
            record.version,
        )
        for record in recorded_provenance
    ) == (
        (
            validation_cycle_id,
            "gse",
            "shared-uad36",
            "2026.1",
        ),
        (
            validation_cycle_id,
            "lender-1",
            "lender-1-overlay",
            "2026.08",
        ),
        (
            validation_cycle_id,
            "amc-1",
            "amc-1-overlay",
            "4.2",
        ),
    )
    assert repository.saved_records == list(recorded_provenance)
    assert len(recorded_provenance) == len(effective_constraint_sets)
