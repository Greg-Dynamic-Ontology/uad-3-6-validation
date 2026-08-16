"""Apply the documented policy for XML Schema wildcards."""

from app.models.schema_model import ComponentProcessingDisposition
from app.services.schema_loader.schema_closure import (
    SchemaComponentInventory,
)


WILDCARD_COMPONENT_KINDS = frozenset({"any", "anyAttribute"})
WILDCARD_POLICY_ACTION = "ignore"
WILDCARD_POLICY_DECISION = "ADR-0014"


def apply_wildcard_policy(
    inventory: SchemaComponentInventory,
) -> tuple[ComponentProcessingDisposition, ...]:
    """Create one deliberate disposition for every wildcard occurrence."""

    return tuple(
        ComponentProcessingDisposition(
            component_kind=occurrence.component_kind,
            source_document=occurrence.source_document,
            source_index=occurrence.source_index,
            action=WILDCARD_POLICY_ACTION,
            governing_decision=WILDCARD_POLICY_DECISION,
            processed=True,
        )
        for occurrence in inventory.occurrences
        if occurrence.component_kind in WILDCARD_COMPONENT_KINDS
    )
