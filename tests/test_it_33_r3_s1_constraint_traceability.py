"""IT-33R3S1 — maintain traceability through generated representations."""

from __future__ import annotations

from importlib import import_module


def _load_traceability_service():
    """Load the production traceability service after the RED test exists."""
    try:
        module = import_module("app.services.constraint_traceability")
    except ModuleNotFoundError:
        return None

    return getattr(module, "build_constraint_traceability", None)


def test_it_33_r3_s1_maintains_traceability_through_generated_representations() -> None:
    """
    Feature: Build governed validation constraints at scale

    Rule: Preserve governed knowledge throughout constraint construction

    Scenario: Maintain traceability through generated representations
    """
    build_constraint_traceability = _load_traceability_service()

    assert build_constraint_traceability is not None, (
        "IT-33R3S1 requires "
        "app.services.constraint_traceability.build_constraint_traceability"
    )

    governed_source_identity = (
        "https://dynamicontology.com/uad36/"
        "source/umdp/fannie-mae/constraint/0100.0007"
    )
    normalized_constraint_identity = (
        "https://dynamicontology.com/uad36/constraint/0100.0007"
    )
    source_provenance = (
        "https://dynamicontology.com/uad36/"
        "source/umdp/fannie-mae/appendix-h-1/"
    )
    executable_representation_identity = (
        "https://dynamicontology.com/uad36/shape/0100.0007"
    )

    traceability = build_constraint_traceability(
        governed_source_identity=governed_source_identity,
        normalized_constraint_identity=normalized_constraint_identity,
        source_provenance=source_provenance,
        executable_representation_identity=(
            executable_representation_identity
        ),
    )

    # The governed source identity remains traceable.
    assert traceability.governed_source_identity == governed_source_identity

    # The normalized constraint identity remains traceable.
    assert (
        traceability.normalized_constraint_identity
        == normalized_constraint_identity
    )

    # Source provenance remains traceable.
    assert traceability.source_provenance == source_provenance

    # The generated executable representation remains traceable
    # to the normalized constraint.
    assert (
        traceability.executable_representation_identity
        == executable_representation_identity
    )
    assert (
        traceability.executable_representation_of
        == normalized_constraint_identity
    )
