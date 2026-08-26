"""Executable acceptance test for IT-22R1S2 default GSE validation."""

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


@dataclass(frozen=True)
class Finding:
    constraint_id: str
    gse_classification: str


@dataclass(frozen=True)
class EngineValidationResult:
    findings: tuple[Finding, ...]


@dataclass
class ShaclValidationGatewaySpy:
    findings: tuple[Finding, ...]
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
        return EngineValidationResult(findings=self.findings)


def _validation_contract() -> Any:
    """Load the governed-validation operation required by IT-22R1S2."""

    try:
        module = import_module(GSE_GOVERNANCE_MODULE)
    except ModuleNotFoundError as error:
        if error.name != GSE_GOVERNANCE_MODULE:
            raise
        pytest.fail(
            "IT-22R1S2 requires app.services.gse_constraint_governance "
            "before default GSE validation can become green.",
            pytrace=False,
        )

    validate = getattr(module, "validate_with_governed_constraints", None)
    assert callable(validate), (
        "IT-22R1S2 requires validate_with_governed_constraints("
        "customer_account_id, validation_request, registry, "
        "validation_gateway, target_gse=None)."
    )
    assert "target_gse" in signature(validate).parameters, (
        "IT-22R1S2 requires validate_with_governed_constraints(...) to "
        "accept target_gse=None so an unselected target applies both GSEs."
    )
    return validate


def test_it_22_r1_s2_validates_against_both_gse_rule_sets_by_default(
) -> None:
    """Apply shared constraints once plus both GSE-specific sets."""

    validate = _validation_contract()
    customer_account_id = "customer-account-1"
    constraint_sets = (
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
    original_constraint_sets = constraint_sets
    registry = GovernedConstraintRegistryStub(constraint_sets)
    findings = tuple(
        Finding(
            constraint_id=next(iter(constraint_set.constraint_ids)),
            gse_classification=constraint_set.gse_classification,
        )
        for constraint_set in constraint_sets
    )
    validation_gateway = ShaclValidationGatewaySpy(findings=findings)
    validation_request = object()

    result = validate(
        customer_account_id,
        validation_request,
        registry,
        validation_gateway,
        target_gse=None,
    )

    assert registry.account_lookups == [customer_account_id]
    assert validation_gateway.calls == [
        {
            "validation_request": validation_request,
            "constraint_sets": constraint_sets,
        }
    ]
    assert tuple(
        finding.gse_classification for finding in result.findings
    ) == (
        "shared",
        "fannie_mae_only",
        "freddie_mac_only",
    )
    assert result.constraint_set_versions == (
        "shared-uad36:2026.1",
        "fannie-mae-uad36:2026.1",
        "freddie-mac-uad36:2026.1",
    )
    assert constraint_sets == original_constraint_sets
