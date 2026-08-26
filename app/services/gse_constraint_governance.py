"""Central governance for versioned GSE constraint sets."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, TypeVar


class GovernedConstraintWeakeningError(ValueError):
    """Reject an account preference that would weaken governed constraints."""


class GovernedConstraintSet(Protocol):
    constraint_set_id: str
    version: str
    constraint_ids: frozenset[str]


ConstraintSet = TypeVar("ConstraintSet", bound=GovernedConstraintSet)


class CustomerConstraintPreferenceRequest(Protocol):
    disabled_constraint_ids: frozenset[str]
    severity_overrides: tuple[tuple[str, str], ...]


class GovernedConstraintRegistry(Protocol[ConstraintSet]):
    def applicable_constraint_sets(
        self,
        customer_account_id: str,
    ) -> tuple[ConstraintSet, ...]: ...


class CustomerPreferenceRepository(Protocol):
    def save(self, preferences: object) -> None: ...


class ValidationGatewayResult(Protocol):
    findings: tuple[object, ...]


class GovernedValidationGateway(Protocol[ConstraintSet]):
    def validate(
        self,
        validation_request: object,
        constraint_sets: tuple[ConstraintSet, ...],
    ) -> ValidationGatewayResult: ...


class ValidationCycleTargetRepository(Protocol):
    def record_target_gse(
        self,
        validation_cycle_id: str,
        target_gse: str,
    ) -> None: ...


@dataclass(frozen=True)
class EffectiveCustomerConstraintPreferences:
    """An accepted account preference that cannot alter governed rules."""

    actor_id: str
    customer_account_id: str
    requested_preferences: CustomerConstraintPreferenceRequest


@dataclass(frozen=True)
class GovernedConstraintValidationResult:
    """Validation output with exact constraint-set version identities."""

    findings: tuple[object, ...]
    constraint_set_versions: tuple[str, ...]
    target_gse: str | None = None


def configure_customer_constraint_preferences(
    actor_id: str,
    customer_account_id: str,
    requested_preferences: CustomerConstraintPreferenceRequest,
    registry: GovernedConstraintRegistry[ConstraintSet],
    preference_repository: CustomerPreferenceRepository,
) -> EffectiveCustomerConstraintPreferences:
    """Accept preferences only when governed applicable rules are unchanged."""

    constraint_sets = registry.applicable_constraint_sets(
        customer_account_id
    )
    applicable_constraint_ids = frozenset(
        constraint_id
        for constraint_set in constraint_sets
        for constraint_id in constraint_set.constraint_ids
    )
    disabled_applicable_constraints = (
        requested_preferences.disabled_constraint_ids
        & applicable_constraint_ids
    )
    overridden_applicable_constraints = {
        constraint_id
        for constraint_id, _ in requested_preferences.severity_overrides
        if constraint_id in applicable_constraint_ids
    }
    if disabled_applicable_constraints or overridden_applicable_constraints:
        raise GovernedConstraintWeakeningError(
            "Customer preferences cannot disable or override an applicable "
            "centrally governed GSE constraint."
        )

    effective_preferences = EffectiveCustomerConstraintPreferences(
        actor_id=actor_id,
        customer_account_id=customer_account_id,
        requested_preferences=requested_preferences,
    )
    preference_repository.save(effective_preferences)
    return effective_preferences


def validate_with_governed_constraints(
    customer_account_id: str,
    validation_request: object,
    registry: GovernedConstraintRegistry[ConstraintSet],
    validation_gateway: GovernedValidationGateway[ConstraintSet],
    target_gse: str | None = None,
    validation_cycle_id: str | None = None,
    validation_cycle_repository: (
        ValidationCycleTargetRepository | None
    ) = None,
) -> GovernedConstraintValidationResult:
    """Apply both GSEs by default or shared plus one selected GSE."""

    constraint_sets = registry.applicable_constraint_sets(
        customer_account_id
    )
    selected_constraint_sets = constraint_sets
    if target_gse is not None:
        target_classifications = {
            "fannie_mae": "fannie_mae_only",
            "freddie_mac": "freddie_mac_only",
        }
        try:
            target_classification = target_classifications[target_gse]
        except KeyError as error:
            raise ValueError(
                f"Unsupported target GSE: {target_gse}"
            ) from error
        if (
            validation_cycle_id is None
            or validation_cycle_repository is None
        ):
            raise ValueError(
                "A selected target GSE requires a validation cycle and "
                "target repository."
            )
        selected_constraint_sets = tuple(
            constraint_set
            for constraint_set in constraint_sets
            if getattr(constraint_set, "gse_classification", None)
            in ("shared", target_classification)
        )
        validation_cycle_repository.record_target_gse(
            validation_cycle_id,
            target_gse,
        )

    gateway_result = validation_gateway.validate(
        validation_request,
        selected_constraint_sets,
    )
    return GovernedConstraintValidationResult(
        findings=tuple(gateway_result.findings),
        constraint_set_versions=tuple(
            f"{constraint_set.constraint_set_id}:{constraint_set.version}"
            for constraint_set in selected_constraint_sets
        ),
        target_gse=target_gse,
    )
