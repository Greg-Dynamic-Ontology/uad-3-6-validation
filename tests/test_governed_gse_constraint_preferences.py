"""Executable tests for IT-22R1S1 governed GSE constraints."""

from __future__ import annotations

from dataclasses import dataclass, field
from importlib import import_module
from typing import Any

import pytest


GSE_GOVERNANCE_MODULE = "app.services.gse_constraint_governance"


@dataclass(frozen=True)
class GovernedConstraintSet:
    constraint_set_id: str
    gse: str
    version: str
    constraint_ids: frozenset[str]
    native_severities: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class CustomerConstraintPreferenceRequest:
    disabled_constraint_ids: frozenset[str] = frozenset()
    severity_overrides: tuple[tuple[str, str], ...] = ()


@dataclass
class GovernedConstraintRegistryStub:
    constraint_sets: tuple[GovernedConstraintSet, ...]
    account_lookups: list[str] = field(default_factory=list)

    def applicable_constraint_sets(
        self,
        customer_account_id: str,
    ) -> tuple[GovernedConstraintSet, ...]:
        self.account_lookups.append(customer_account_id)
        return self.constraint_sets


@dataclass
class CustomerPreferenceRepositorySpy:
    saved_preferences: list[object] = field(default_factory=list)

    def save(self, preferences: object) -> None:
        self.saved_preferences.append(preferences)


@dataclass(frozen=True)
class EngineValidationResult:
    findings: tuple[object, ...]


@dataclass
class ShaclValidationGatewaySpy:
    calls: list[dict[str, object]] = field(default_factory=list)

    def validate(
        self,
        validation_request: object,
        constraint_sets: tuple[GovernedConstraintSet, ...],
    ) -> EngineValidationResult:
        self.calls.append(
            {
                "validation_request": validation_request,
                "constraint_sets": constraint_sets,
            }
        )
        return EngineValidationResult(findings=())


def _governance_contract() -> tuple[Any, Any, type[Exception]]:
    """Load the constraint-governance contract expected by IT-22R1S1."""

    try:
        module = import_module(GSE_GOVERNANCE_MODULE)
    except ModuleNotFoundError as error:
        if error.name != GSE_GOVERNANCE_MODULE:
            raise
        pytest.fail(
            "IT-22R1S1 requires app.services.gse_constraint_governance "
            "before governed preferences can become green.",
            pytrace=False,
        )

    configure_preferences = getattr(
        module,
        "configure_customer_constraint_preferences",
        None,
    )
    validate = getattr(
        module,
        "validate_with_governed_constraints",
        None,
    )
    weakening_error = getattr(
        module,
        "GovernedConstraintWeakeningError",
        None,
    )
    assert callable(configure_preferences), (
        "IT-22R1S1 requires configure_customer_constraint_preferences("
        "actor_id, customer_account_id, requested_preferences, registry, "
        "preference_repository)."
    )
    assert callable(validate), (
        "IT-22R1S1 requires validate_with_governed_constraints("
        "customer_account_id, validation_request, registry, "
        "validation_gateway)."
    )
    assert isinstance(weakening_error, type) and issubclass(
        weakening_error,
        Exception,
    ), "IT-22R1S1 requires GovernedConstraintWeakeningError."
    return configure_preferences, validate, weakening_error


def _fannie_constraint_set() -> GovernedConstraintSet:
    return GovernedConstraintSet(
        constraint_set_id="fannie-mae-uad36",
        gse="fannie_mae",
        version="2026.1",
        constraint_ids=frozenset({"UAD1001", "UAD1005"}),
        native_severities=(
            ("UAD1001", "Fatal"),
            ("UAD1005", "Fatal"),
        ),
    )


@pytest.mark.parametrize(
    ("actor_id", "requested_preferences"),
    [
        (
            actor_id,
            preferences,
        )
        for actor_id in (
            "human-user-owner",
            "human-user-validator",
            "software-client-1",
        )
        for preferences in (
            CustomerConstraintPreferenceRequest(
                disabled_constraint_ids=frozenset({"UAD1001"}),
            ),
            CustomerConstraintPreferenceRequest(
                severity_overrides=(("UAD1005", "Warning"),),
            ),
        )
    ],
    ids=[
        "owner-cannot-disable",
        "owner-cannot-downgrade",
        "user-cannot-disable",
        "user-cannot-downgrade",
        "software-client-cannot-disable",
        "software-client-cannot-downgrade",
    ],
)
def test_it_22_r1_s1_rejects_preferences_that_weaken_constraints(
    actor_id: str,
    requested_preferences: CustomerConstraintPreferenceRequest,
) -> None:
    """Reject disabling or severity downgrades for every account actor."""

    configure_preferences, _, weakening_error = _governance_contract()
    customer_account_id = "customer-account-1"
    constraint_set = _fannie_constraint_set()
    original_constraint_set = constraint_set
    registry = GovernedConstraintRegistryStub((constraint_set,))
    preferences = CustomerPreferenceRepositorySpy()

    with pytest.raises(weakening_error):
        configure_preferences(
            actor_id,
            customer_account_id,
            requested_preferences,
            registry,
            preferences,
        )

    assert preferences.saved_preferences == []
    assert constraint_set == original_constraint_set


def test_it_22_r1_s1_reports_the_governed_constraint_set_version() -> None:
    """Apply the complete registry set and identify its version in results."""

    _, validate, _ = _governance_contract()
    customer_account_id = "customer-account-1"
    constraint_set = _fannie_constraint_set()
    registry = GovernedConstraintRegistryStub((constraint_set,))
    validation_gateway = ShaclValidationGatewaySpy()
    validation_request = object()

    result = validate(
        customer_account_id,
        validation_request,
        registry,
        validation_gateway,
    )

    assert validation_gateway.calls == [
        {
            "validation_request": validation_request,
            "constraint_sets": (constraint_set,),
        }
    ]
    assert result.constraint_set_versions == (
        "fannie-mae-uad36:2026.1",
    )
    assert result.findings == ()
