from __future__ import annotations

from pathlib import Path

from app.services.generate_logical_schema_graph import (
    generate_logical_schema_graph,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]

LOGICAL_SCHEMA_GRAPH = (
    PROJECT_ROOT
    / "docs"
    / "milestones"
    / "milestone-1"
    / "artifacts"
    / "logical-schema.ttl"
)


def test_serialized_logical_schema_model_exists() -> None:
    """
    Milestone 1 contract:
    The Logical Schema Model shall be persisted as an RDF/Turtle artifact.
    """
    generated_file = generate_logical_schema_graph(
        output_file=LOGICAL_SCHEMA_GRAPH,
    )

    assert generated_file == LOGICAL_SCHEMA_GRAPH
    assert LOGICAL_SCHEMA_GRAPH.is_file(), (
        "Serialized Logical Schema Model does not exist: "
        f"{LOGICAL_SCHEMA_GRAPH}"
    )
    assert LOGICAL_SCHEMA_GRAPH.stat().st_size > 0, (
        "Serialized Logical Schema Model is empty: "
        f"{LOGICAL_SCHEMA_GRAPH}"
    )
