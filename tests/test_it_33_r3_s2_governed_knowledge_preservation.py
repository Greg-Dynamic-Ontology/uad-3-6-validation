"""IT-33R3S2 — do not replace governed knowledge with implementation-specific knowledge."""

from __future__ import annotations

from importlib import import_module


def _load_preservation_service():
    """Load the production preservation service after the RED test exists."""
    try:
        module = import_module("app.services.governed_knowledge_preservation")
    except ModuleNotFoundError:
        return None

    return getattr(module, "preserve_governed_knowledge", None)


def test_it_33_r3_s2_does_not_replace_governed_knowledge_with_implementation_specific_knowledge() -> None:
    """
    Feature: Build governed validation constraints at scale

    Rule: Preserve governed knowledge throughout constraint construction

    Scenario: Do not replace governed knowledge with implementation-specific knowledge
    """
    preserve_governed_knowledge = _load_preservation_service()

    assert preserve_governed_knowledge is not None, (
        "IT-33R3S2 requires "
        "app.services.governed_knowledge_preservation."
        "preserve_governed_knowledge"
    )

    governed_constraint_identity = (
        "https://dynamicontology.com/uad36/constraint/0100.0007"
    )
    governed_requirement = (
        "Provide the address line for the subject property physical address."
    )

    executable_representation_identity = (
        "https://dynamicontology.com/uad36/shape/0100.0007"
    )
    implementation_structure = {
        "technology": "SHACL",
        "constraint_component": "sh:MinCountConstraintComponent",
        "minimum_count": 1,
    }

    result = preserve_governed_knowledge(
        governed_constraint_identity=governed_constraint_identity,
        governed_requirement=governed_requirement,
        executable_representation_identity=(
            executable_representation_identity
        ),
        implementation_structure=implementation_structure,
    )

    # The executable representation implements the governed constraint.
    assert (
        result.executable_representation_of
        == governed_constraint_identity
    )

    # Implementation-specific identity does not replace governed identity.
    assert (
        result.governed_constraint_identity
        == governed_constraint_identity
    )
    assert (
        result.governed_constraint_identity
        != executable_representation_identity
    )

    # Governed meaning remains the source of meaning.
    assert result.governed_requirement == governed_requirement

    # Implementation-specific structure remains implementation detail.
    assert result.implementation_structure == implementation_structure
    assert result.meaning_source == "governed-constraint"
