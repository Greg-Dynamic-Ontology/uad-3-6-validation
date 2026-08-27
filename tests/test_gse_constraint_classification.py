"""Executable acceptance tests for IT-24R1S1 GSE classification."""

from __future__ import annotations

from dataclasses import dataclass, field
from importlib import import_module
from typing import Any

import pytest


GSE_GOVERNANCE_MODULE = "app.services.gse_constraint_governance"


@dataclass
class GovernedConstraintRepositorySpy:
    saved_constraints: list[object] = field(default_factory=list)

    def save(self, constraint: object) -> None:
        self.saved_constraints.append(constraint)


def _classification_contract() -> tuple[Any, type[Exception]]:
    """Load the registration contract required by IT-24R1S1."""

    try:
        module = import_module(GSE_GOVERNANCE_MODULE)
    except ModuleNotFoundError as error:
        if error.name != GSE_GOVERNANCE_MODULE:
            raise
        pytest.fail(
            "IT-24R1S1 requires app.services.gse_constraint_governance "
            "before GSE classification can become green.",
            pytrace=False,
        )

    register = getattr(module, "register_gse_constraint", None)
    classification_error = getattr(
        module,
        "GseConstraintClassificationError",
        None,
    )
    assert callable(register), (
        "IT-24R1S1 requires register_gse_constraint("
        "constraint_id, classifications, repository)."
    )
    assert isinstance(classification_error, type) and issubclass(
        classification_error,
        Exception,
    ), "IT-24R1S1 requires GseConstraintClassificationError."
    return register, classification_error


@pytest.mark.parametrize(
    "classification",
    [
        "fannie_mae_only",
        "freddie_mac_only",
        "shared",
    ],
    ids=["fannie-mae-only", "freddie-mac-only", "shared"],
)
def test_it_24_r1_s1_classifies_a_gse_constraint_exactly_once(
    classification: str,
) -> None:
    """Register each allowed, mutually exclusive GSE classification."""

    register, _ = _classification_contract()
    repository = GovernedConstraintRepositorySpy()

    registered = register(
        "UAD-GSE-001",
        frozenset({classification}),
        repository,
    )

    assert registered.constraint_id == "UAD-GSE-001"
    assert registered.gse_classification == classification
    assert repository.saved_constraints == [registered]


@pytest.mark.parametrize(
    "classifications",
    [
        frozenset(),
        frozenset({"fannie_mae_only", "shared"}),
    ],
    ids=["no-classification", "multiple-classifications"],
)
def test_it_24_r1_s1_rejects_a_constraint_not_classified_exactly_once(
    classifications: frozenset[str],
) -> None:
    """Reject registration with zero or multiple classifications."""

    register, classification_error = _classification_contract()
    repository = GovernedConstraintRepositorySpy()

    with pytest.raises(classification_error):
        register(
            "UAD-GSE-001",
            classifications,
            repository,
        )

    assert repository.saved_constraints == []
