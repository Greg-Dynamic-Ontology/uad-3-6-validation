from __future__ import annotations

from pathlib import Path

from app.services.logical_schema_serializer import (
    serialize_logical_schema_model,
)
from app.services.schema_loader.schema_loader import SchemaLoader


PROJECT_ROOT = Path(__file__).resolve().parents[2]

COMBINED_SCHEMA = (
    PROJECT_ROOT
    / "specs"
    / "UAD"
    / "GSE_UAD_3.6.0_v1.3"
    / "Combined"
    / "GSE_UAD_3.6.0_v1.3.xsd"
)

LOGICAL_SCHEMA_GRAPH = (
    PROJECT_ROOT
    / "docs"
    / "milestones"
    / "milestone-1"
    / "artifacts"
    / "logical-schema.ttl"
)


def generate_logical_schema_graph(
    schema_path: Path = COMBINED_SCHEMA,
    output_file: Path = LOGICAL_SCHEMA_GRAPH,
) -> Path:
    """
    Load the Logical Schema Model and persist it as RDF/Turtle.
    """
    logical_schema_model = SchemaLoader().load(schema_path)

    return serialize_logical_schema_model(
        logical_schema_model,
        output_file,
    )


def main() -> None:
    output_file = generate_logical_schema_graph()
    print(f"Generated {output_file}")


if __name__ == "__main__":
    main()
