"""Composition of governed validation constraint sets."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol, TypeVar

from app.services.gse_constraint_governance import (
    GovernedConstraintWeakeningError,
)


ConstraintSet = TypeVar("ConstraintSet")
Constraint = TypeVar("Constraint")


class ContradictoryGovernedConstraintsError(ValueError):
    """Reject active governed requirements that cannot both be true."""


class ConstraintSetProvenanceRepository(Protocol):
    def save(self, provenance_record: object) -> None: ...


class AppliedConstraintSet(Protocol):
    authority: str
    constraint_set_id: str
    version: str


@dataclass(frozen=True)
class AppliedConstraintSetProvenance:
    """The exact identity of a governed set applied to one cycle."""

    validation_cycle_id: str
    authority: str
    constraint_set_id: str
    version: str


def record_applied_constraint_set_provenance(
    validation_cycle_id: str,
    effective_constraint_sets: tuple[AppliedConstraintSet, ...],
    repository: ConstraintSetProvenanceRepository,
) -> tuple[AppliedConstraintSetProvenance, ...]:
    """Record authority, set identity, and version for every applied set."""

    provenance_records = tuple(
        AppliedConstraintSetProvenance(
            validation_cycle_id=validation_cycle_id,
            authority=constraint_set.authority,
            constraint_set_id=constraint_set.constraint_set_id,
            version=constraint_set.version,
        )
        for constraint_set in effective_constraint_sets
    )
    for provenance_record in provenance_records:
        repository.save(provenance_record)
    return provenance_records


def deduplicate_constraints_by_canonical_identity(
    constraints: tuple[Constraint, ...],
) -> tuple[Constraint, ...]:
    """Keep the first occurrence of each explicit canonical identity."""

    seen_canonical_ids: set[object] = set()
    effective_constraints: list[Constraint] = []
    for constraint in constraints:
        canonical_id = getattr(
            constraint,
            "canonical_constraint_id",
            None,
        )
        if canonical_id is not None:
            if canonical_id in seen_canonical_ids:
                continue
            seen_canonical_ids.add(canonical_id)
        effective_constraints.append(constraint)
    return tuple(effective_constraints)


def compose_effective_constraint_sets(
    selected_gse_constraint_sets: tuple[ConstraintSet, ...],
    governed_overlays: tuple[ConstraintSet, ...],
    as_of: date | None = None,
) -> tuple[ConstraintSet, ...]:
    """Combine only active, effective, and applicable governed sets."""

    evaluation_date = as_of or date.today()
    applicable_gse_sets = tuple(
        constraint_set
        for constraint_set in selected_gse_constraint_sets
        if _is_active_and_applicable(constraint_set, evaluation_date)
    )
    applicable_overlays = tuple(
        constraint_set
        for constraint_set in governed_overlays
        if _is_active_and_applicable(constraint_set, evaluation_date)
    )
    _prevent_gse_constraint_weakening(
        applicable_gse_sets,
        applicable_overlays,
    )
    _reject_contradictory_constraints(
        (*applicable_gse_sets, *applicable_overlays)
    )
    return (*applicable_gse_sets, *applicable_overlays)


def _prevent_gse_constraint_weakening(
    gse_constraint_sets: tuple[object, ...],
    governed_overlays: tuple[object, ...],
) -> None:
    """Reject overlay directives that weaken an applicable GSE rule."""

    gse_severities = {
        constraint.constraint_id: severity
        for constraint_set in gse_constraint_sets
        for constraint in getattr(constraint_set, "constraints", ())
        if (severity := getattr(constraint, "severity", None)) is not None
    }
    gse_constraint_ids = frozenset(gse_severities)
    severity_rank = {
        "info": 0,
        "warning": 1,
        "error": 2,
        "fatal": 3,
    }

    for overlay in governed_overlays:
        disabled_ids = frozenset(
            getattr(overlay, "disabled_constraint_ids", frozenset())
        )
        if disabled_ids & gse_constraint_ids:
            raise GovernedConstraintWeakeningError(
                "A governed overlay cannot disable an applicable GSE "
                "constraint."
            )

        for constraint_id, replacement_severity in getattr(
            overlay,
            "severity_overrides",
            (),
        ):
            if constraint_id not in gse_severities:
                continue
            native_severity = gse_severities[constraint_id]
            if severity_rank.get(
                replacement_severity.casefold(),
                -1,
            ) < severity_rank.get(native_severity.casefold(), -1):
                raise GovernedConstraintWeakeningError(
                    "A governed overlay cannot downgrade an applicable "
                    "GSE constraint."
                )


def _reject_contradictory_constraints(
    constraint_sets: tuple[object, ...],
) -> None:
    """Reject distinct required values for the same governed subject."""

    required_values: dict[str, object] = {}
    for constraint_set in constraint_sets:
        for constraint in getattr(constraint_set, "constraints", ()):
            requirement_key = getattr(
                constraint,
                "requirement_key",
                None,
            )
            if requirement_key is None:
                continue
            required_value = getattr(
                constraint,
                "required_value",
                None,
            )
            if (
                requirement_key in required_values
                and required_values[requirement_key] != required_value
            ):
                raise ContradictoryGovernedConstraintsError(
                    "Active governed constraints require contradictory "
                    f"values for {requirement_key}."
                )
            required_values[requirement_key] = required_value


def _is_active_and_applicable(
    constraint_set: object,
    as_of: date,
) -> bool:
    """Evaluate lifecycle dates and validation-cycle applicability."""

    is_active = getattr(constraint_set, "is_active", True)
    effective_from = getattr(constraint_set, "effective_from", date.min)
    effective_through = getattr(
        constraint_set,
        "effective_through",
        None,
    )
    applies_to_validation_cycle = getattr(
        constraint_set,
        "applies_to_validation_cycle",
        True,
    )
    return bool(
        is_active
        and effective_from <= as_of
        and (
            effective_through is None
            or as_of <= effective_through
        )
        and applies_to_validation_cycle
    )
