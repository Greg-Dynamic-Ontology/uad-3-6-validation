"""Executable acceptance tests for IT-22R1S3 target-GSE selection."""

from __future__ import annotations

from dataclasses import dataclass, field
from importlib import import_module
from inspect import signature
from typing import Any

import pytest


GSE_GOVERNANCE_MODULE = "app.services.gse_constraint_governance"


@dataclass(frozen=True)
class GovernedConstraintSet:
    constraint_set_id: str
    gse_classification: str
    version: str
    constraint_ids: frozenset[str]


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
class ValidationCycleTargetRepositorySpy:
    recorded_targets: list[tuple[str, str]] = field(default_factory=list)

    def record_target_gse(
        self,
        validation_cycle_id: str,
        target_gse: str,
    ) -> None:
        self.recorded_targets.append((validation_cycle_id, target_gse))


@dataclass(frozen=True)
class Finding:
    constraint_id: str
    gse_classification: str


@dataclass(frozen=True)
class EngineValidationResult:
    findings: tuple[Finding, ...]


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
        return EngineValidationResult(
            findings=tuple(
                Finding(
                    constraint_id=next(
                        iter(constraint_set.constraint_ids)
                    ),
                    gse_classification=(
                        constraint_set.gse_classification
                    ),
                )
                for constraint_set in constraint_sets
            )
        )


def _validation_contract() -> Any:
    """Load the selected-GSE operation required by IT-22R1S3."""

    try:
        module = import_module(GSE_GOVERNANCE_MODULE)
    except ModuleNotFoundError as error:
        if error.name != GSE_GOVERNANCE_MODULE:
            raise
        pytest.fail(
            "IT-22R1S3 requires app.services.gse_constraint_governance "
            "before target-GSE selection can become green.",
            pytrace=False,
        )

    validate = getattr(module, "validate_with_governed_constraints", None)
    assert callable(validate), (
        "IT-22R1S3 requires validate_with_governed_constraints(...)."
    )
    required_parameters = {
        "target_gse",
        "validation_cycle_id",
        "validation_cycle_repository",
    }
    missing_parameters = required_parameters - set(
        signature(validate).parameters
    )
    assert not missing_parameters, (
        "IT-22R1S3 requires validate_with_governed_constraints(...) to "
        "accept target_gse, validation_cycle_id, and "
        "validation_cycle_repository."
    )
    return validate


def _constraint_sets() -> tuple[GovernedConstraintSet, ...]:
    return (
        GovernedConstraintSet(
            constraint_set_id="shared-uad36",
            gse_classification="shared",
            version="2026.1",
            constraint_ids=frozenset({"UAD-SHARED-001"}),
        ),
        GovernedConstraintSet(
            constraint_set_id="fannie-mae-uad36",
            gse_classification="fannie_mae_only",
            version="2026.1",
            constraint_ids=frozenset({"UAD-FANNIE-001"}),
        ),
        GovernedConstraintSet(
            constraint_set_id="freddie-mac-uad36",
            gse_classification="freddie_mac_only",
            version="2026.1",
            constraint_ids=frozenset({"UAD-FREDDIE-001"}),
        ),
    )


@pytest.mark.parametrize(
    ("target_gse", "specific_classification", "specific_set_id"),
    [
        (
            "fannie_mae",
            "fannie_mae_only",
            "fannie-mae-uad36",
        ),
        (
            "freddie_mac",
            "freddie_mac_only",
            "freddie-mac-uad36",
        ),
    ],
    ids=["fannie-mae", "freddie-mac"],
)
def test_it_22_r1_s3_selects_a_target_gse_without_weakening_constraints(
    target_gse: str,
    specific_classification: str,
    specific_set_id: str,
) -> None:
    """Record the target and apply shared plus selected-specific rules."""

    validate = _validation_contract()
    customer_account_id = "customer-account-1"
    validation_cycle_id = "validation-cycle-1"
    constraint_sets = _constraint_sets()
    original_constraint_sets = constraint_sets
    registry = GovernedConstraintRegistryStub(constraint_sets)
    cycle_repository = ValidationCycleTargetRepositorySpy()
    validation_gateway = ShaclValidationGatewaySpy()
    validation_request = object()
    selected_constraint_sets = (
        constraint_sets[0],
        next(
            constraint_set
            for constraint_set in constraint_sets
            if constraint_set.gse_classification
            == specific_classification
        ),
    )

    result = validate(
        customer_account_id,
        validation_request,
        registry,
        validation_gateway,
        target_gse=target_gse,
        validation_cycle_id=validation_cycle_id,
        validation_cycle_repository=cycle_repository,
    )

    assert cycle_repository.recorded_targets == [
        (validation_cycle_id, target_gse)
    ]
    assert registry.account_lookups == [customer_account_id]
    assert validation_gateway.calls == [
        {
            "validation_request": validation_request,
            "constraint_sets": selected_constraint_sets,
        }
    ]
    assert tuple(
        finding.gse_classification for finding in result.findings
    ) == ("shared", specific_classification)
    assert result.target_gse == target_gse
    assert result.constraint_set_versions == (
        "shared-uad36:2026.1",
        f"{specific_set_id}:2026.1",
    )
    assert constraint_sets == original_constraint_sets
